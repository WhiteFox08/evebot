import discord
import asyncio
import configparser
import aiohttp
import json
import sqlite3

config = configparser.ConfigParser()
config.read('config.ini')

VerifedID = config['default']['VerifedID']
FailedID = config['default']['FailedID']
NoapiID = config['default']['NoapiID']
token = config['default']['token']
allianceID = config['default']['allianceID']
killmail_channel_ID = config['default']['killmail_channel_ID']
api_filter_url = config['default']['api_filter_url']
headers =  {'User-Agent' : 'https://zkillboard.com/', 'Maintainer':'whitefox008@gmail.com' ,'Accept-Encoding': 'gzip'}
VerifedR = discord.Object(id=VerifedID)
FailedR = discord.Object(id=FailedID)
NoapiR = discord.Object(id=NoapiID)

conn = sqlite3.connect('api.db')

c = conn.cursor()

try:
    c.execute('''CREATE TABLE api
                (disid text UNIQUE,
                 disname text ,
                 keyid text UNIQUE,
                 vcode text UNIQUE)''')
except:
    print('DB -> Table already created!')


mlist = []

client = discord.Client()




async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def killboard_task():
    await client.wait_until_login()
    async with aiohttp.ClientSession(headers=headers) as session:
        json_payload = await fetch(session, api_filter_url)
        jsonresponce = json.loads(json_payload)
        initfetch = jsonresponce[0]['killID'] #get initkm

        while not client.is_closed:
            json_payload = await fetch(session, 'https://zkillboard.com/allianceID/99006805/api/afterKillID/{0}/json/'.format(initfetch))
            jsonresponce = json.loads(json_payload)
            try:
                initfetch = jsonresponce[0]['killID']  # keep it going lads

            except:
                pass

            else:
                killurl = ''
                for item in jsonresponce:
                    killurl = 'https://zkillboard.com/kill/' + str(item['killID']) + ' \n'
                    killurl = killurl + killurl
                await client.send_message(discord.Object(id=killmail_channel_ID), killurl)

            await asyncio.sleep(50)  # lets not fucking slam the server with request 50 is pretty fucking moderate

async def update_members():
    await client.wait_until_ready()
    async with aiohttp.ClientSession() as session:
        while not client.is_closed:
            for member in client.get_all_members():
                if member.name == client.user.name:  #Remove thotty
                    continue

                try:
                    print(member.name, member.id)
                    c.execute("update api set disname = \'{0}\' where disid = \'{1}\'".format(member.name,member.id))
                    conn.commit()
                except sqlite3.DatabaseError as e:
                    print('DB -> Username add Error Raised: ', e)
                    pass

                try:
                    c.execute('insert into api (disid) values(?)',[member.id]) #add disid's into table
                    conn.commit()

                except sqlite3.DatabaseError as e:
                    pass

                c.execute("select keyid from api where disid = \'{0}\'".format(member.id))
                (k,) = c.fetchone()
                c.execute("select vcode from api where disid = \'{0}\'".format(member.id))
                (v,) = c.fetchone()

                if not k:
                    print('DB -> USER <{0}> HAS NO KEY / API: {1} / {2}'.format(member.name, k, v))
                    await client.replace_roles(member,NoapiR)

                    continue

                async with session.get('https://api.eveonline.com/account/characters.xml.aspx?keyID={0}&vCode={1}'.format(k,v)) as resp:
                    payload = await resp.text()

                    if allianceID in payload:
                        print('DB -> USER <{0}> PASSED API CHECK'.format(member.name))
                        try: await client.replace_roles(member, VerifedR)
                        except: print('DISCORD BOT -> {0} FAILED TO ADD ROLE'.format(member.name))
                        pass

                    else:
                        print('DB -> USER <{0}> FAILED API CHECK'.format(member.name))
                        try: await client.replace_roles(member, FailedR)
                        except: print('DISCORD BOT -> {0} FAILED TO ADD ROLE'.format(member.name))

                await asyncio.sleep(3)
            await asyncio.sleep(3600)

@client.event
async def on_ready():
    await client.change_presence(game=discord.Game(name='Rolling out of home since Dominion'))
@client.event
async def on_member_join(member):

    server = member.server
    fmt = 'Welcome {0.mention} to {1.name}! to verify your account, create an api using this predefined key and then type !verify in chat! \n http://community.eveonline.com/support/api-key/CreatePredefined?accessMask=50331648'
    await client.send_message(server, fmt.format(member, server))
@client.event
async def on_message(message):
    if message.content.startswith('!verify'):
        await client.delete_message(message)
        msg = await client.send_message(message.author, '❗ **Paste your KeyID** {0.author.mention}'.format(message))
        keyid = await client.wait_for_message(author=message.author)
        k = keyid.content

        await client.edit_message(msg, '❗ **Paste your Vcode {0.author.mention}**'.format(message))
        vcode = await client.wait_for_message(author=message.author)
        v = vcode.content

        await client.edit_message(msg, '⭕ **Verifying API! {0.author.mention}**'.format(message))
        await asyncio.sleep(3)

        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.eveonline.com/account/characters.xml.aspx?keyID={0}&vCode={1}'.format(k, v)) as resp:
                text = await resp.text()
                if allianceID in text:
                    Pass = await client.edit_message(msg,'✅ **ACCESS GRANTED** Welcome to Wormageddon {0.author.mention}!'.format(message))
                    await client.replace_roles(message.author, VerifedR)

                    try:
                        c.execute("UPDATE api SET keyid = \'{0}\', vcode = \'{1}\'  WHERE disid = \'{2}\'".format(k,v,message.author.id))
                        conn.commit()

                    except sqlite3.DatabaseError as e:
                        print('DB -> Raised error when adding {0}\'s keyid and vcode: --> '.format(message.author),e)
                        conn.rollback()

                    await asyncio.sleep(15)
                    await client.delete_message(Pass)

                else:
                    Fail = await client.edit_message(msg,'❌ ***{0.author.mention} you have entered a invalid api you dork try again using !verify*** ❌ \n https://vgy.me/5nObgz.jpg'.format(message))
                    await asyncio.sleep(25)
                    await client.delete_message(Fail)

client.loop.create_task(killboard_task())
client.loop.create_task(update_members())
client.run(token)
