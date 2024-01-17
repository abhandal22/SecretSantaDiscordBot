import discord, random
from discord.ext import commands
import mysql.connector
 
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)
 
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="dbtest"
)

cursor = mydb.cursor(dictionary=True, buffered=True)

async def check(ctx):
    try:
        cursor.execute(f"SELECT * FROM t{ctx.guild.id}")
        cursor.fetchall()
    except Exception:
        id = ctx.guild.id
        id = str(id)

        cursor.execute(f"""
                        CREATE TABLE t{id} (
                        ID VARCHAR(250) PRIMARY KEY,
                        MESSAGE VARCHAR(250),
                        EXCLUSION VARCHAR(250));""")

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))


async def dbTest(ctx, id, message, exclusion):
    cursor.execute(f"DELETE FROM t{ctx.guild.id} WHERE ID = {id}")
    sqlAdd = f"INSERT INTO t{ctx.guild.id} (ID, MESSAGE, EXCLUSION) VALUES (%s, %s, %s)"
    val = (id, message, exclusion)
    cursor.execute(sqlAdd, val)


async def store(ctx, user):
    await dbTest(ctx, user[0], user[1], user[2])

async def send(ctx, users):
    for user in users:
        u = bot.get_user(user[0])
        await u.send(bot.get_user(user[1]))

async def inDatabase(ctx, user:discord.User):
    cursor.execute(f"SELECT ID from t{ctx.guild.id}")
    users = cursor.fetchall()
    for id in users:
        if int(id["ID"]) == user.id:
            return True
    return False

# Return True if the user's exclued id is the same as the parameter id
async def isExculded(ctx, currUser:discord.User, userGiftee:discord.User):
    if await inDatabase(ctx, currUser):
        cursor.execute(f"SELECT EXCLUSION from t{ctx.guild.id} where ID = {currUser.id}")
        id = cursor.fetchone()
        return int(id["EXCLUSION"]) == userGiftee.id
    else:
        return False

async def clearGiftees(ctx, users):
    for user in users:
        cursor.execute(f"SELECT MESSAGE from t{ctx.guild.id} where ID = {user.id}")
        cursor.execute(f"UPDATE t{ctx.guild.id} SET MESSAGE = {1} WHERE ID = {user.id}")

async def isGifter(ctx, gifter:discord.User, giftee:discord.User):
    if (await inDatabase(ctx, gifter)) and (await inDatabase(ctx, giftee)):
        cursor.execute(f"SELECT MESSAGE from t{ctx.guild.id} where ID = {giftee.id}")
        gifteeID = cursor.fetchone()
        return int(gifteeID["MESSAGE"]) == gifter.id
    else:
        return False

async def hasExclusion(ctx, user:discord.User):
    if await inDatabase(ctx, user):
        cursor.execute(f"SELECT EXCLUSION from t{ctx.guild.id} where ID = {user.id}")
        excludedID = cursor.fetchone()
        return not (int(excludedID["EXCLUSION"]) == 0)
    else:
        return False
    
async def keepExclusion(ctx, user:discord.User):
    cursor.execute(f"SELECT EXCLUSION from t{ctx.guild.id} where ID = {user.id}")
    excludedID = cursor.fetchone()
    return int(excludedID["EXCLUSION"])


@bot.command(name="santa", help="Draws everyone a name from the names given. Enter 3 or more names with no duplicates. Will take into account given Example: '!santa @Test1 @Test2 @Test3' would give each user a giftee with no cycles.")
async def secretSanta(ctx, *users:discord.User):
    await check(ctx)
    users = list(users)
    await clearGiftees(ctx, users)
    lou1 = list(users)
    lou2 = lou1.copy()
    allUsers = []
    numUsers = len(lou1)
    cont = True
    i = 0
    for user in lou1:
        if lou1.count(user) != 1: 
            cont = False
    
    if cont == False:
        await ctx.send("Please do not enter the same user multiple times when using this command.")
    
    if len(lou1) < 3: 
        cont = False
        await ctx.send("A minimum of 3 users is required to use this command.")
    
    stop = 0
    while i < numUsers and cont:
        singleUser = []
        giftee = random.choice(lou2)
        excluded = await isExculded(ctx, lou1[i], giftee)
        gifter = await isGifter(ctx, lou1[i], giftee)

        if stop > 150:
            await ctx.send("Too many exclusions, try removing some. " +
                           "If this shouldn't be the case, enter the users with exclusions before others " + 
                           "in the '!santa' command")
            allUsers = []
            break
        else:
            stop += 1
    
        if (lou1[i] != giftee) and (not excluded) and (not gifter):
            lou2.remove(giftee)
            singleUser.append(lou1[i].id)   # Adds the "gifters" id
            singleUser.append(giftee.id)    # Adds the "giftees" id
            if await hasExclusion(ctx, lou1[i]):
                singleUser.append(await keepExclusion(ctx, lou1[i]))
            else:
                singleUser.append(0)            # Adds a default value for "giftee" exclusion
            allUsers.append(singleUser)
            i += 1
            await store(ctx, singleUser)

    await send(ctx, allUsers)

@bot.command(help="Set a user to exclude in the draw. Example: '!exclude @Test1' would make is so I can't draw @Test1 as a giftee")
async def exclude(ctx, excludeUser:discord.User):
    if await inDatabase(ctx, ctx.author):
        cursor.execute(f"SELECT EXCLUSION from t{ctx.guild.id} where ID = {ctx.author.id}")
        cursor.execute(f"UPDATE t{ctx.guild.id} SET EXCLUSION = {excludeUser.id} WHERE ID = {ctx.author.id}")
    else:
        await dbTest(ctx, ctx.author.id, 1, excludeUser.id)
    await ctx.send("Your exclusion has been recorded.")

@bot.command(help="Resets your exclusion to be no one. Example: '!resetExclusion'")
async def resetExclusion(ctx):
    if await inDatabase(ctx, ctx.author):
        cursor.execute(f"SELECT EXCLUSION from t{ctx.guild.id} where ID = {ctx.author.id}")
        cursor.execute(f"UPDATE t{ctx.guild.id} SET EXCLUSION = {0} WHERE ID = {ctx.author.id}")
    await ctx.send("Your exclusion has been reset.")
    
@bot.command(help="Sends you a DM to remind you who your giftee is. Example: '!reminder'")
async def reminder(ctx):
    if await inDatabase(ctx, ctx.author):
        cursor.execute(f"SELECT MESSAGE from t{ctx.guild.id} where ID = {ctx.author.id}")
        user = cursor.fetchone()
        if int(user["MESSAGE"]) != 1:
            user = bot.get_user(int(user["MESSAGE"]))
            await ctx.author.send(f"Your giftee is {user}")
        else:
            await ctx.author.send("You do not have a giftee assigned, please use the !santa command in your server to have one assigned.")

bot.run('BOT KEY HERE')
