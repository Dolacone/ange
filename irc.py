# Import some necessary libraries.
import socket, ssl
import random
from ConfigParser import SafeConfigParser

configFile = 'irc.conf'
config = SafeConfigParser()
config.read(configFile)

import ange
import glob, os

# Some basic variables used to configure the bot        
server = config.get('irc', 'server') # Server
port   = int(config.get('irc', 'port'))   # Port
channel = config.get('irc', 'channel') # Channel
channel_pass = config.get('irc', 'channel_pass')
botnick = config.get('irc', 'nickname') + str(random.randint(0, 10000)) # Your bots nick

def ping(): # This is our first function! It will respond to server Pings.
  ircsock.send("PONG :pingis\n")  

def sendmsg(msg): # This is the send message function, it simply sends messages to the channel.
  ircsock.send("PRIVMSG ##"+ channel +" :>>> "+ msg +"\n") 

def joinchan(chan, chan_pass=""): # This function is used to join channels.
  ircsock.send("JOIN ##"+ chan + " " + chan_pass +"\n")

def hello(): # This function responds to a user that inputs "Hello Mybot"
  ircsock.send("PRIVMSG "+ channel +" :Hello!\n")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server, port)) # Here we connect to the server using the port 6667
ircsock = ssl.wrap_socket(s)
ircsock.send("USER "+ botnick +" "+ botnick +" "+ botnick +" :This bot is a result of a tutoral covered on http://shellium.org/wiki.\n") # user authentication
ircsock.send("NICK "+ botnick +"\n") # here we actually assign the nick to the bot

joinchan(channel, channel_pass) # Join the channel using the functions we previously defined

def ange_sys_command(target, command):
  if command == 'start':
    commandString = "python2.7 ange.py %s auto & 2&>/dev/null" % (target)
  if command == 'stop':
    commandString = "ps -ax | grep 'python ange.py %s auto' | awk '{print $1}' | xargs kill -9" % (target)
  os.popen(commandString)
  return

def ange_conf_command(target, config, value):
  tmpConfigFile = '%s/ange.conf' % target
  tmpConfig = SafeConfigParser()
  tmpConfig.read(tmpConfigFile)
  tmpConfig.set('ange', config, value)
  fp = open(tmpConfigFile, 'wb')
  tmpConfig.write(fp)
  fp.close()
  return

def ange_conf_print(target):
  tmpConfigFile = '%s/ange.conf' % (target)
  tmpConfig = SafeConfigParser()
  tmpConfig.read(tmpConfigFile)
  for confItem in tmpConfig.options('ange'):
    sendmsg("%s = %s" % (confItem, tmpConfig.get('ange', confItem)))
  return

while 1: # Be careful with these! it might send you to an infinite loop
  ircmsg = ircsock.recv(2048) # receive data from the server
  ircmsg = ircmsg.strip('\n\r') # removing any unnecessary linebreaks.
  print(ircmsg) # Here we print what's coming from the server

  if ircmsg.find("PING :") != -1: # if the server pings us then we've got to respond!
    ping()
    
#  ircmsg = ircmsg.lower()

  # normal command
  if len(ircmsg.split(":.ange ")) == 2:
    try:
      parsed = ircmsg.split(":.ange ")[1].split(' ')
      parsed = filter(None, parsed)
      if len(parsed) != 2:
        sendmsg("parsing failed, format: .ange [target] [command]")
        continue
      target  = parsed[0]
      command = parsed[1]
      sendmsg("command received: %s %s" % (target, command))
      if target == "all":
        for configFile in sorted(glob.glob('*/ange.conf')):
          response = ange.execution(configFile, command)
          sendmsg('%-6s - %s' % (configFile.split('/')[0], response))
      else:
        response = ange.execution(target+'/ange.conf', command)
        sendmsg('%-6s - %s' % (target, response))
      sendmsg("command completed")
    except Exception as exceptMsg:
      sendmsg("exception - %s" % (exceptMsg))
      
  # system command
  if len(ircmsg.split(':.angebot ')) == 2:
    try:
      parsed = ircmsg.split(".angebot ")[1].split(' ')
      parsed = filter(None, parsed)
      if len(parsed) != 2:
        sendmsg("parsing failed, format: .angebot [target] [command]")
        continue
      target  = parsed[0]
      command = parsed[1]
      sendmsg("command received: %s %s" % (target, command))
      if target == "all":
        for configFile in glob.glob('*/ange.conf'):
          ange_sys_command(configFile.split('/')[0], command)
      else:
        ange_sys_command(target, command)
      sendmsg("command completed")
    except Exception as exceptMsg:
      sendmsg("exception - %s" % (exceptMsg))
      
  # config command
  if len(ircmsg.split(':.angeconf ')) == 2:
    try:
      parsed = ircmsg.split(".angeconf ")[1].split(' ')
      parsed = filter(None, parsed)
      if len(parsed) == 1:
        target = parsed[0]
        ange_conf_print(target)
        continue
      
      if len(parsed) != 3:
        sendmsg("parsing failed, format: .angebot [target] [config] [value]")
        continue
      target  = parsed[0]
      configItem = parsed[1]
      configValue = parsed[2]
      sendmsg("command received: %s %s %s" % (target, configItem, configValue))
      if target == "all":
        for configFile in glob.glob('*/ange.conf'):
          ange_conf_command(configFile.split('/')[0], configItem, configValue)
      else:
        ange_conf_command(target, configItem, configValue)
        ange_conf_print(target)
      sendmsg("command completed")
    except Exception as exceptMsg:
      sendmsg("exception - %s" % (exceptMsg))

  # log uploader
  for logFile in glob.glob('*/log'):
    try:
      fh = open(logFile, 'r')
      fh_content = fh.read().rstrip('\n')
      fh.close()
      sendmsg('%-6s - %s' % (logFile.split('/')[0], fh_content))
      os.remove(logFile)
    except IOError:
      pass
