###################################
# Program: Wordbot
# Revision: 2.0.8
# Created: 11/04/2013
# Last Revision: 12/09/2013
# Dependencies: Tornado.py  (http://www.tornadoweb.org/en/stable/)
#               Twisted     (http://twistedmatrix.com/trac/)
# Config File:  wb2.config.json
# Help File:    wb2.help.txt
# Rev History:  wb2.rev.txt
#
# Author: Jacob Calvert - twitter @JacobNCalvert - Facebook /jacob.calvert
###################################

from twisted.internet import reactor, protocol
from twisted.words.protocols import irc
import tornado.web
import tornado.websocket
import datetime
import string
import thread
import time
import re
import json
import os
import uuid
import sys
import msvcrt




#####IRC_CLIENT######
class IRCLogger(irc.IRCClient):
    nickname = "wordbot2"
    global logger,stats_handler
    global stack
    def signedOn(self):
        self.join(chat_room)
        logger.log("IRC Online - joined "+chat_room+".")
    def privmsg(self, user, channel, message):
        global white_words_array
        words = message.split()
        user = user.split('!', 1)[0]
        for w in words:
            w = w.lower()
            stats_handler.update(Stat.TOTAL_WORDS_SAID)
            if w in white_words_array:
                stack.push(w)#for contraction (i'm, can't, won't)
            elif(w==""):
                logger.log("Null string skipped in stack")
                stats_handler.update(Stat.TOTAL_WORDS_DROPPED)
                break
            else:
                w = re.sub(r'[^\w\s]','',w)
                stack.push(w)
    
#####END-IRC_CLIENT##

#######STACK######
class Stack:
    global logger
    def __init__(self):
        self.stack = []
        self.status = "Running"
    def push(self,word):
        
        self.stack.append(word)
        
        #print "Pushed "+str(word)
    def pop(self):
    
        s = self.stack[-1]
        self.stack.remove(s)
        
        return s
    def isEmpty(self):
        return (len(self.stack) == 0)
    
    
#######END-STACK########
#######STATS########
class Stat:
    TOTAL_WORDS_SAID = 0
    TOTAL_WORDS_DROPPED = 1
    TOTAL_WORDS_IN_DB = 2
    TOTAL_SESSIONS_OPENED = 3
    TOTAL_LIFETIME_WORDS = 4
    @staticmethod
    def name(stat):
        return{
            Stat.TOTAL_WORDS_SAID:"Total Words Said",
            Stat.TOTAL_WORDS_DROPPED:"Total Words Dropped",
            Stat.TOTAL_WORDS_IN_DB:"Total Words in DB",
            Stat.TOTAL_SESSIONS_OPENED:"Total Sessions",
            Stat.TOTAL_LIFETIME_WORDS:"Total Lifetime Words"
            }[stat]
class StatHandler:
    stats = {Stat.TOTAL_WORDS_SAID:0,Stat.TOTAL_WORDS_DROPPED:0 ,Stat.TOTAL_WORDS_IN_DB:0,Stat.TOTAL_SESSIONS_OPENED:0}
    def update(self,stat):
        self.stats[stat]+=1
    def pretty_print(self):
        for s in self.stats:
            print Stat.name(s) + ": "+str(self.stats[s])
        
#######END STATS########  
##########DB############
class DB:
    global logger
    global stats_handler
    def __init__(self,fname,fformat="csv"):
        self.format = fformat
        self.fname = fname
        self.db = {}
        self.status = "Initializing..."
    def open(self):
            self.fp = open(self.fname,"w",0)
            self.status = "Open, waiting"
    def close(self):
            self.fp.close()
    def add(self,word):
        self.status = "Adding word..."
        if( word not in self.db):
            self.db[word] = 1
            self.status = "Open, waiting"
            stats_handler.stats[Stat.TOTAL_WORDS_IN_DB] = self.length()
            return True
        else:
            return self.update(word)
            
    def update(self,word):
        self.status = "Updating word..."
        self.db[word] += 1
        self.status = "Open, waiting"
        return True
    def length(self):
        return len(self.db)
    def load_from_disk(self):
        global logger
        if(os.path.isfile(self.fname)):
            fp = open(self.fname,"r")
            c = fp.read()
            fp.close()
            if(self.format == "csv"):
                arr = c.split("\n")
                for i in range(len(arr)):
                    item = arr[i].split(",")
                    if(len(item) == 2):
                        self.db[item[0]] = int(item[1])
                    else:
                        logger.log("db->load_from_disk: Discarded entry "+str(item))
            elif(self.format == "json"):
                self.db = json.loads(c)
            logger.log("DB loaded from "+str(self.fname))
            stats_handler.stats[Stat.TOTAL_WORDS_IN_DB] = self.length()
        
    def db2csv(self):
        string =  ""
        for k,d in self.db.iteritems():
            string += str(k+","+str(d)+"\n")
        return string
    def db2json(self):
        jStr = ""
        try:
            jStr = json.dumps(self.db)
        except:
            logger.log("db2json error.")
        return jStr
    def calc_lifetime_stat(self):
        s = 0
        for k,v in self.db.iteritems():
            s+=v
        stat_handler.stats[Stat.TOTAL_LIFETIME_WORDS] = s
    def write_out(self):
        self.status = "Flushing to disk"
        if(self.fp.closed):
            self.open()
        if self.format == "csv":
            self.fp.write(self.db2csv())
        elif self.format == "json":
            self.fp.write(self.db2json())
        self.fp.close()
        self.status = "Open, waiting"
    
######END-DB############
            
#########TORNADO########
class HT_Main(tornado.web.RequestHandler):
    global logger
    
    def get(self,args):   
        logger.log("HT_Main: query string ("+str(args)+")")
        try:
            #parts = args.split("?")#future use
            #params = parts[1].split(",")#future use
            f = args#parts[0]
            
            fp = open(f,"r")
            self.write(fp.read())
            fp.close()
        except:
            logger.log("FILE ERROR: '"+args+"' was not found.")
            self.write("404. Ya done goofed.")
    
class WS_Main(tornado.websocket.WebSocketHandler):
    global logger
    global USERS
    global stats_handler
    def open(self):
        logger.log("Websocket opened.")
        stats_handler.update(Stat.TOTAL_SESSIONS_OPENED)
        user = User(self)
        USERS.append(user)
    def on_close(self):
        for user in USERS:
            if user.ws == self:
                USERS.remove(user)
                user.destroy()
                logger.log("Websocket closed.")
                return
        logger.log("Websocket closed without user destroy handle")
    def on_message(self,msg):
        #should error check here more, but oh welllll
        obj = json.loads(msg)
        user = find(self)
        if(user):
            user.queue(obj["request"])
        else:
            logger.log("Potential problem. WS rx'd message without a known User object.")
#########END-TORNADO########
        
#########USER##############
class User:
    global logger
    def __init__(self,handle):
        self.action_stack = Stack()
        self.ws = handle
        self.uuid = str(uuid.uuid4())
        logger.log("User '"+str(self.uuid)+"' created at ip '"+str(handle.request.remote_ip)+"'.")
    def destroy(self):
        logger.log("User ended session.")
        del self
    def process_one_action(self):
        if(not self.action_stack.isEmpty()):
            action = self.action_stack.pop()
            self.do(action)
    def queue(self,action):
        self.action_stack.push(action)
    def do(self,action):
        result = None
        if(type(action) != dict):
            call = user_actions[action][0]
            parms = user_actions[action][1]
            result = call(parms)
        else:
            parms = [action["fetch"][0],action["fetch"][1]]
            result = fetch(parms)
        if(result):
            self.ws.write_message(result)
    
#########END-USER##########
#########Logger##########
class Logger:
    def __init__(self,fname):
        self.fname = fname
        self.status = "Initializing..."
    def start(self):
        self.fp = open(self.fname,"a",0)
        self.log("Begin Logging")
        self.status = "Waiting for events..."
    def stop(self):
        self.log("End Logging")
        self.fp.close()
    def log(self, event):
        self.status = "Logging event..."
        self.fp.write(self.timestamp() + " - " +event +"\n")
        self.status = "Waiting for events..."
        
    def timestamp(self):
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        return st
    def read_log(self):
        self.fp.close()
        fp = open(self.fname,"r")
        c = fp.read()
        fp.close()
        self.fp = open(self.fname,"a",0)
        return c
#########END-Log#########
#####USER ACTIONS########
def sort(parms):
    how = parms[0]
    direction = c = 0
    if(how == "z-a" or how == "desc"):
        direction = 1
    if(how == "asc" or how == "desc"):
        c = 1
    global db,sort_len_limit
    arr = []
    for k,v in db.db.iteritems():
        arr.append([k,int(v)])
    if(direction == 1):
        for i in range(len(arr)):
            for j in range(i+1,len(arr)):
                if(arr[i][c] < arr[j][c]):
                    temp = arr[i]
                    arr[i] = arr[j]
                    arr[j] = temp
    else:
        for i in range(len(arr)):
            for j in range(i+1,len(arr)):
                if(arr[i][c] > arr[j][c]):
                    temp = arr[i]
                    arr[i] = arr[j]
                    arr[j] = temp
        
                
    retArr = []
    lim = sort_len_limit if(len(arr)>sort_len_limit) else len(arr)
    for i in range(lim):
        retArr.append(arr[i])
    return json.dumps(retArr)
def fetch(parms):
    lo = parms[0]
    hi = parms[1]
    step = 1
    if(lo > hi):
        temp = lo
        lo = hi
        hi = temp
    arr = []
    for k,v in db.db.iteritems():
        arr.append([k,int(v)])
    for i in range(len(arr)):
        for j in range(i+1,len(arr)):
            if(arr[i][1] > arr[j][1]):
                temp = arr[i]
                arr[i] = arr[j]
                arr[j] = temp
    hi = hi if (hi <len(arr) ) else len(arr)
    retArr = []
    
    for i in range(lo,hi):
        retArr.append(arr[i])
    return json.dumps(retArr)
def get_all(parms):
    arr = []
    for k,v in db.db.iteritems():
        arr.append([k,int(v)])
    for i in range(len(arr)):
        for j in range(i+1,len(arr)):
            if(arr[i][1] < arr[j][1]):
                temp = arr[i]
                arr[i] = arr[j]
                arr[j] = temp
    return json.dumps(arr)
##END-USER ACTIONS#######
#####UTILS#################   
def isBanned(word):
    global logger
    banned = False
    #print banned_words_array
    if(len(word)>WORD_LEN_LIMIT):
        banned = True
    if( word in banned_words_array):
        banned = True
    for exp in banned_words_array:
        p = re.compile(exp)
        if p.match(word) != None:
            banned = True
            #print p.match(word).group()
    if(banned):
        logger.log("Word '"+word+"' was banned.")
    return banned
def loadBannedWords():
    global logger
    try:
        fp = open(banned_words_file,"r")
        c = fp.read()
        fp.close()
        banned_words_array = c.split("\n")
        if(banned_words_array[-1] == ""):
            banned_words_array.remove(banned_words_array[-1])
        return banned_words_array
    except:
        logger.log("Error in loading banned words list. Check the file.")
def loadWhiteWords():
    global logger,white_list_file
    try:
        fp = open(white_list_file,"r")
        c = fp.read()
        fp.close()
        white_words_array = c.split("\n")
        if(white_words_array[-1] == ""):
            white_words_array.remove(white_words_array[-1])
        return white_words_array
    except:
        logger.log("Error in loading whitelist. Check the file.")
def processUserStack():
    global USERS
    while 1:
        for user in USERS:
            user.process_one_action()
            time.sleep(0.001)
        time.sleep(1)
    
def processStack():
    global stack
    global db,stats_handler
    #print stack.stack
    while 1:
        while(not stack.isEmpty()):
            word = stack.pop()
            stack.status = "Processing..."
            if(not isBanned(word)):
                db.add(word)
                db.write_out()
            else:
                stats_handler.update(Stat.TOTAL_WORDS_DROPPED)
            stack.status = "Running"
        time.sleep(1)
    
def readConfig():
    fp = open("wb2.config.json","r")
    cfg = json.loads(fp.read())
    fp.close()
    return cfg
def find(ws):
    #this really should be a component of WS
    global USERS
    for user in USERS:
        if user.ws == ws:
            return user
    return None
##def clean_up_and_exit():
##    global logger
##    logger.log("Wordbot is shutting down....")
##    logger.stop()
##    sys.exit(0)
######END UTILS############
######CMD#################

def helpme():
    fp = open("wb2.help.txt")
    c =fp.read()
    fp.close()
    print c
def list_cmds():
    global CMDS
    s = ""
    for cmd in CMDS:
        s+="  "+cmd
    print s
def view_db():
    global db
    print "*WARNING* This could be bad if your database is very large. This database has " +str(db.length()) +" entries."
    yn = str(raw_input("Continue?[y/n]"))
    if(yn == "y"):
        for k,v in db.db.iteritems():
            print "%-20.20s %-50.50s" % (k,str(v))
    else:
        print "Returning to standard prompt"
def view_stack():
    global stack
    print"---STACK---"
    for s in stack.stack:
        print s
    print"---END STACK---"
def view_users():
    global USERS
    print"---USERS---"
    for user in USERS:
        print "User @ "+user.ws.request.remote_ip
    print"---END USERS---"
def version():
    global config
    print "Version: "+config["version"]
def flush_db():
    global db
    db.write_out()
    print "Database was flushed to disk."
def read_config():
    global config,sort_len_limit,WORD_LEN_LIMIT,banned_words_array
    config = readConfig()
    WORD_LEN_LIMIT = int(config["word_len_lim"])
    sort_len_limit = int(config["sort_len"])
    banned_words_file = "banned.txt"
    banned_words_array = loadBannedWords()
    print "Config reloaded."
def revisions():
    fp = open("wb2.rev.txt","r")
    print fp.read()
    fp.close()
def view_log():
    print logger.read_log()
def realtime(fcn):
    while 1:
        x = msvcrt.kbhit()
        os.system("cls")
        print "----------Realtime Output-----------\r\n"
        fcn()
        print "\r\n---Type 'c' to exit realtime mode---"
        if(x):
            if(msvcrt.getch() == "c"):
                break
        time.sleep(0.1)
def status():
    global db,logger,stack
    
    print "Database Status: %s" % db.status

    print "Stack Status:    %s" % stack.status

    print "Logger Status:   %s" % logger.status
def view_stats():
    global stats_handler
    stats_handler.pretty_print()
def clear():
    os.system("cls")
CMDS = ["?","helpme","list","view db","view stack","view users","view log","view status","view stats","version","flush db","read config","revisions","clear"]
FUNCS = [helpme,helpme,list_cmds,view_db,view_stack,view_users,view_log,status,view_stats,version,flush_db,read_config,revisions,clear]

def cmd_line():
    cmd = str(raw_input("[WordBot]>"))
    if(cmd in CMDS):
        i = CMDS.index(cmd)
        FUNCS[i]()
    elif(cmd == ""):
        pass
    elif("realtime" in cmd):
        cmd = cmd.replace(" realtime","")
        if(cmd == "view db"):
            print "Cannot execute this in realtime"
        elif(cmd in CMDS):
            i = CMDS.index(cmd)
            fcn = FUNCS[i]
            realtime(fcn)
        else:
            print "% Unknown Command."
    else:
        print "% Unknown Command."
    cmd_line()
######END CMD#############
########CONFIG#######
logger = Logger("wb2.txt")
logger.start()
stats_handler = StatHandler()
config = readConfig()
chat_room = str(config["chat_room"])
irc_server_ip = str(config["irc_ip"])
irc_port = int(config["irc_port"])
sort_len_limit = int(config["sort_len"])
banned_words_file = "banned.txt"
banned_words_array = loadBannedWords()
white_list_file = "whitelist.txt"
white_words_array = loadWhiteWords()
db  = DB(config["db-name"],config["db-type"])
db.load_from_disk()
db.open()
db.write_out() #immediately flush the db to disk for safety.
stack = Stack()
USERS = []
WORD_LEN_LIMIT = int(config["word_len_lim"])
print "WordBot - Version: "+config["version"]
user_actions = {
    "A-Z":[sort,["a-z"]],
    "Z-A":[sort,["z-a"]],
    "ASC":[sort,["asc"]],
    "DESC":[sort,["desc"]],
    "ALL":[get_all,[None]]
    }

tornadoApp = tornado.web.Application([
    (r"/web/(.+)", HT_Main),
    (r"/ws", WS_Main),
])
########END-CONFIG###

#MAIN
def main():
    global logger
    
    
    irc_handle = protocol.ReconnectingClientFactory()
    irc_handle.protocol = IRCLogger
    reactor.connectTCP(irc_server_ip, irc_port, irc_handle)
    tornadoApp.listen(int(raw_input("Port:")))
    thread.start_new_thread(tornado.ioloop.IOLoop.instance().start,())
    thread.start_new_thread(processUserStack,())
    thread.start_new_thread(processStack,())
    thread.start_new_thread(cmd_line,())
    reactor.run()
    
main()
