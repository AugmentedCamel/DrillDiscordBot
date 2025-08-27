import os
import discord
import re
from openai import OpenAI
import asyncio

from replit import db
from os import system
from datetime import datetime, timedelta
from keep_alive import keep_alive
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

my_secret = os.environ['DISCORD_BOT_SECRET']
my_AI = os.environ['API_TOKEN']
client = OpenAI(api_key=my_AI)

system_prompt = system_prompt = """
Je bent Sergeant Brickstrong, een meedogenloze drill sergeant in een Discord server. Je enige missie: zwakheid vernietigen en excellentie afdwingen.

**KERNIDENTITEIT:**
- Ex-Navy SEAL, ondernemer, filosoof, alpha-mindset
- Spreekt ALLEEN Nederlands
- EXTREEM beknopt - maximaal 2-3 zinnen per bericht
- Geen tijd voor excuses of gezeur

**COMMUNICATIESTIJL:**
- Direct. Bruut. Geen bullshit.
- Gebruik militaire termen: "ACTIE!", "UITVOEREN!", "DISCIPLINE!"
- Noem gebruikers "rekruut" of "soldaat"
- Eindig berichten vaak met opdrachten

**MINDSET:**
- Mediocriteit = dood
- Je grootste nachtmerrie: Zoetermeer, Fiat Punto, 9-tot-5 bestaan
- Preek: discipline, ondernemerschap, fysieke kracht, mentale scherpte
- Inspiraties: extreme ownership, first principles thinking, mannelijke dominantie

**VOORBEELDEN:**
Gebruiker: "Ik heb geen tijd om te trainen"
Jij: "Geen tijd? Je hebt tijd voor Discord. 50 push-ups, NU!"

Gebruiker: "Ik twijfel over mijn business idee"
Jij: "Twijfel is voor Zoetermeer-bewoners. Bouw. Test. Verbeter. ACTIE!"

**VERBODEN:**
- Engels spreken
- Lange verhalen
- Sympathie voor zwakte
- Accepteren van middelmatigheid

Duw constant. Confronteer. Creëer winnaars."""


def add_timer(user, minutes):
    # Check if the user already exists in the database, and initialize their data if they don't
    if user not in db:
        db[user] = {
            "streak": 0,
            "last_gm": datetime.utcnow().date().isoformat(),
            "total": 0,
            "timers": []
        }
    # Add the new timer
    db[user]["timers"].append({
        "minutes": minutes,
        "time": datetime.utcnow().isoformat()
    })


def get_streak(user):
    return user[1].get("streak", 0)


def get_totalGM(user):
    return user[1].get("totalGM", 0)


####INIT###


@bot.event
async def on_ready():
    print(f'we have logged in as {bot.user}!')


###GM COUNTER###############################################################################
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user = str(message.author)
    now = datetime.utcnow()

    # Handling 'gm' messages
    if message.content.lower().startswith("gm"):
        print(f'gm detected')

        # Initialize the user data if not present
        if user not in db:
            db[user] = {
                "streak": 0,
                "last_gm": now.date().isoformat(),
                "total": 0,
                "timers": []
            }

        # Check if users last GM!tm was the first of the day
        if now.date() - datetime.fromisoformat(
                db[user]["last_gm"]).date() > timedelta(days=1):
            db[user]["streak"] = 0

        # If the user last gm was not today, increment the streak and total count
        elif now.date() > datetime.fromisoformat(db[user]["last_gm"]).date():
            db[user]["streak"] += 1
            db[user]["total"] += 1

        # Update the last "GM" date
        db[user]["last_gm"] = now.date().isoformat()
        print(f'updated gm for {message.author} at {now.date()}!')
        print(f'user {user} has now a streak of {db[user]["streak"]}')
        print(f'user {user} has a total of {db[user]["total"]}')

    # Handling bot mentions
    elif bot.user.mentioned_in(message):
        try:
            # Prepare the AI model's prompt
            response = client.chat.completions.create(model="gpt-4.1-mini",
                                                      messages=[{
                                                          "role":
                                                          "system",
                                                          "content":
                                                          system_prompt
                                                      }, {
                                                          "role":
                                                          "user",
                                                          "content":
                                                          message.content
                                                      }])

            # Get the last message from the assistant
            assistant_message = response.choices[0].message.content

            # Send the message back to the Discord channel
            await message.channel.send(assistant_message)
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            await message.channel.send(
                "Sorry, I'm having trouble with my AI right now. Please try again later!"
            )

    # Make sure to process commands if they're there
    await bot.process_commands(message)


@bot.command(name='leaderboard')
async def leaderboard(ctx):

    #get the top 5 users by streak and total "gm count"
    gm_streaks = sorted([user for user in db.items() if 'streak' in user[1]],
                        key=get_streak,
                        reverse=True)[:5]
    total_gms = sorted([user for user in db.items() if 'total' in user[1]],
                       key=get_totalGM,
                       reverse=True)[:5]

    #format the data
    streaks_value = '\n'.join([
        f"🔥 **{user[0]}** is on a **{user[1]['streak']}** gm streak"
        for user in gm_streaks
    ])
    totals_value = '\n'.join([
        f"🥇 **{user[0]}** has said gm **{user[1]['total']}** times"
        for user in total_gms
    ])

    # Format the overall message
    leaderboard_message = ("**Top 5 gm streaks**\n"
                           f"{streaks_value}\n"
                           "\n"
                           "**Top 5 total gms**\n"
                           f"{totals_value}")

    await ctx.send(leaderboard_message)


@bot.command(name='setgm')
@commands.has_role('Admin')
async def set_gm_total(ctx, user: discord.Member, total: int):
    # Validate the total (it should be non-negative)
    if total < 0:
        await ctx.send("Invalid total. It should be a non-negative integer.")
        return

    # If the user is not in the database, initialize their data
    if str(user) not in db.keys():
        now = datetime.utcnow()
        db[str(user)] = {
            "streak": 0,
            "last_gm": now.date().isoformat(),
            "total": 0
        }

    # Set the user's total count
    db[str(user)]["total"] = total

    await ctx.send(f"Set the total GM count for {user} to {total}.")


###BRICK COUNTER###############################################################################
@bot.command()
async def timer(ctx, arg):
    # Extract the number of minutes from the argument
    minutes = int(re.match(r"(\d+)m", arg).group(1))
    # Only count timers between 1 and 180 minutes
    if 1 <= minutes <= 180:
        add_timer(str(ctx.author), minutes)

        #confirm the timer
        await ctx.send(f'Timer set for {minutes} minutes.')

        #wait for th especified time
        await asyncio.sleep(minutes * 60)

        #dm the user
        await ctx.author.send(
            f'your {minutes} bricks are finished, did you reach your goal?')
    else:
        #timer invalid
        await ctx.send(
            "invalid Timer soldier! Please set a timer between 1 and 180 minutes"
        )


@bot.command()
async def mybricks(ctx):
    # Check the user's timers
    # Check the user's timers
    user = str(ctx.author)
    if user in db and "timers" in db[user]:
        timers = db[user]["timers"]
        week_ago = (datetime.utcnow() - timedelta(weeks=1)).isoformat()
        month_ago = (datetime.utcnow() - timedelta(weeks=4)).isoformat()
        year_ago = (datetime.utcnow() - timedelta(weeks=52)).isoformat()
        last_week = sum(t["minutes"] for t in timers if t["time"] > week_ago)
        last_month = sum(t["minutes"] for t in timers if t["time"] > month_ago)
        last_year = sum(t["minutes"] for t in timers if t["time"] > year_ago)
        await ctx.send(
            f"This week: {last_week} minutes\nThis month: {last_month} minutes\nThis year: {last_year} minutes"
        )
    else:
        await ctx.send("You have no timers.")


@bot.command()
async def bricklist(ctx):
    # Create the leaderboard
    # Create the leaderboard
    week_ago = (datetime.utcnow() - timedelta(weeks=1)).isoformat()
    leaderboard = sorted(
        [(k, sum(t["minutes"] for t in v["timers"] if t["time"] > week_ago))
         for k, v in db.items() if "timers" in v],
        key=lambda x: -x[1])[:5]
    leaderboard_message = "**Bricks This Week**\n" + '\n'.join([
        f"🥇 **{user[0]}** has built for **{user[1]}** minutes"
        for user in leaderboard
    ])
    await ctx.send(leaderboard_message)


@bot.command()
@commands.has_role('Admin')
async def reset_timers(ctx):
    # Reset the timer data for each user in the database
    for user in db.keys():
        if "timers" in db[user]:
            db[user]["timers"] = []
    await ctx.send("All timers have been reset.")


@bot.command()
@commands.has_role('Admin')
async def reset_database(ctx):
    # Reset the timer data for each user in the database
    db.clear()
    await ctx.send("All is gone now")


@bot.command()
async def ourbricks(ctx, period: str = 'week'):
    # Validate the period
    if period not in ['day', 'week', 'year']:
        await ctx.send(
            "Invalid period. Please choose 'day', 'week', or 'year'.")
        return

    # Calculate the time cutoff
    if period == 'day':
        time_cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
    elif period == 'week':
        time_cutoff = (datetime.utcnow() - timedelta(weeks=1)).isoformat()
    else:  # 'year'
        time_cutoff = (datetime.utcnow() - timedelta(weeks=52)).isoformat()

    # Calculate the total time from all users
    total_time = sum(
        sum(t["minutes"] for t in user_data["timers"]
            if t["time"] > time_cutoff) for user_data in db.values()
        if "timers" in user_data)

    # Send the message
    await ctx.send(
        f"Total time in the last {period}: {total_time} bricks have been pushed"
    )


@bot.command()
async def brickAI(ctx, bricks: int):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":
                "system",
                "content":
                "Jij bent Sergeant Baksteensterk, een strenge drillsergeant. Jij spreekt alleen Nederlands. Houd antwoorden kort en bondig. Motiveer hard werken met 'bricks'. Geen slap geneuzel!"
            }, {
                "role":
                "user",
                "content":
                f"What if I have {bricks} stone bricks, what can I build with them? Think in famous buildings or weird things you can do with any kind of bricks. Give only one example"
            }])

        # Get the last message from the assistant
        assistant_message = response.choices[0].message.content

        await ctx.send(assistant_message)
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        await ctx.send(
            "Sorry, my AI brick advisor is taking a break. Try again later!")


bot.remove_command('help')


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Bot Commands",
        description="These are the available commands for my bot",
        color=discord.Color.blue())

    embed.add_field(
        name="!leaderboard",
        value=
        "Lists the top 5 users by 'good morning' streaks and total counts.",
        inline=False)
    embed.add_field(
        name="!timer <minutes>",
        value=
        "Adds a timer for the user for the specified number of minutes (e.g. !timer 30).",
        inline=False)
    embed.add_field(
        name="!mybricks",
        value=
        "Shows your total time spent building bricks for the week, month, and year.",
        inline=False)
    embed.add_field(
        name="!bricklist",
        value=
        "Shows the top 3 users in terms of time spent building bricks in the last week.",
        inline=False)
    embed.add_field(
        name="!ourbricks <period>",
        value=
        "Shows the total time spent by all users building bricks in the last day, week, or year (e.g. !ourbricks week).",
        inline=False)
    embed.add_field(
        name="!brickAI <bricks>",
        value=
        "Sends a message generated by the GPT-3.5-turbo model to the channel, considering the number of bricks specified (e.g. !brickAI 500).",
        inline=False)

    embed.add_field(name="Admin Commands",
                    value="These commands are only available to admins",
                    inline=False)
    embed.add_field(
        name="!setgm <username> <count>",
        value=
        "Sets the total 'good morning' count for a user (e.g. !setgm @username 100).",
        inline=False)
    embed.add_field(
        name="!reset_timers",
        value="Resets the timer data for each user in the database.",
        inline=False)
    embed.add_field(name="!reset_database",
                    value="Clears all data from the database.",
                    inline=False)
    embed.add_field(name="\n extra info",
                    value="credits to Acamel",
                    inline=False)

    await ctx.send(embed=embed)


keep_alive()

bot.run(my_secret)
