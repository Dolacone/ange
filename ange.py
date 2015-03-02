import httplib, gzip, re, time, sys, os, glob
from StringIO import StringIO
from lxml.html.clean import Cleaner
from lxml import etree
from ConfigParser import SafeConfigParser
import logging, SingleLogHandler

class DropFileHandler(logging.Handler):
  def __init__(self, folder):
    logging.Handler.__init__(self)
    self.logFile = '%s/log' % (folder)
  def emit(self, record):
    fileDropper = open(self.logFile, 'w')
    fileDropper.write(record.message)
    fileDropper.close()

ange_header  = None
ange_botName = None
config = None

# root logger
_log_format = logging.Formatter('%(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)
# stream output
#log_sh = logging.StreamHandler(sys.stdout)
#log_sh.setFormatter(logging.Formatter('%(message)s'))
#log_sh.setLevel(logging.DEBUG)
#log.addHandler(log_sh)

def html_cleaner(content):
  args = {
    "javascript": True,
    "page_structure": True,
    "style": True
  }
  cleaner = Cleaner(**args)
  content_cleaned = cleaner.clean_html(content)
  return content_cleaned

def ange_request(path):
  time.sleep(1)
  # filter http if exist
  if (path.find('http://') == 0):
    path = re.match('http://.*?(/.*)', path).group(1)
  pageName = re.findall('\/(\w+);', path)[0]
  logging.debug(pageName)
  print path
  # drop log for specified pages
  if pageName in ['RaidBossComingPage', 'RaidHelpOutRedirectPage', 'RaidResultWinPage']:
    logging.info(pageName)
  
  while True:
    try:
      conn = httplib.HTTPConnection("web.ange-app.com")
      conn.request("GET", path, headers=ange_header)
      response = conn.getresponse()
      retCode = response.status
      if (retCode == 302):
        next_url = response.getheader('location')
        return ange_request(next_url)
        #return "302: %s" % (response.getheader('location'))
      else:
        buf = StringIO(response.read())
        content = gzip.GzipFile(fileobj=buf)
        content = content.read()
        content_html = html_cleaner(content)
        parser = etree.HTMLParser()
        content_lxml = etree.parse(StringIO(content_html), parser)
        return content_lxml
    except:
      continue

_sp = -1
_sp_max = -1
_bp = -1
_bp_max = -1
_exp = -1
_exp_max = -1
_jsessionid='9708A0E605F8A5E6ED0418925C0BBD7B.avmap15'
TARGET_ACTION_LIST = ['e', 'f'] # do action if e(quest item) and f(sync up) occurs
_raidBoss = False
_helpBoss = False
_clanBattle = False

def ange_MyPage():
  global _sp, _sp_max, _bp, _bp_max, _exp, _exp_max, _jsessionid, _raidBoss, _helpBoss, _clanBattle
  MyPage = ange_request('/ange/user/MyPage;jsessionid=%s' % (_jsessionid))
  _sp      = int(MyPage.xpath("//span[@id='prm_head_ap']/text()")[0])
  _sp_max  = int(MyPage.xpath("//span[@id='prm_head_ap_max']/text()")[0])
  _bp      = int(MyPage.xpath("//span[@id='prm_head_bp']/text()")[0])
  _bp_max  = int(MyPage.xpath("//span[@id='prm_head_bp_max']/text()")[0])
  _exp     = int(MyPage.xpath("//span[@id='prm_head_exp']/text()")[0])
  _exp_max = int(MyPage.xpath("//span[@id='prm_head_exp_max']/text()")[0])
  _jsessionid = re.findall('jsessionid=(.*)\" ',etree.tostring(MyPage))[0]
  _raidBoss = True if MyPage.xpath('//div[@id="attention"]//li[@id="bossAt"]/a/@href') else False
  _helpBoss = True if MyPage.xpath('//div[@id="attention"]//li[@id="helpAt"]/a/@href') else False
  _clanBattle = True if MyPage.xpath('//p[@class="claconLink"]//a/@href') else False
  return MyPage

def ange_StageSelectPage():
  MyPage = ange_MyPage()
  StageSelectPage_link = re.findall('href=\"(.*StageSelectPage.*)\" ', etree.tostring(MyPage))[1]
  StageSelectPage = ange_request(StageSelectPage_link)
  return StageSelectPage

def doQuest(adam=False):
  # find stage link from MyPage
  MyPage = ange_MyPage()
  StageSelectPage_link = re.findall('href=\"(.*StageSelectPage.*)\" ', etree.tostring(MyPage))[1]
  
  # find map from stage
  StageSelectPage = ange_request(StageSelectPage_link)
  adamSPList = StageSelectPage.xpath('//span[@class="adamSP"]//span[@class="fontGreen"]/text()')
  adamSP = int(adamSPList[0]) if len(adamSPList) > 0 else 0
  if (adam) and (adamSP > 0):
    MapSelectPage_link = re.findall('href=\"(.*MapSelectPage.*)\" ', etree.tostring(StageSelectPage))[-1]
  else:
    MapSelectPage_link = re.findall('href=\"(.*MapSelectPage.*)\" ', etree.tostring(StageSelectPage))[0]
  
  # find next area in map
  MapSelectPage = ange_request(MapSelectPage_link)
  try:
    # look for next area
    QuestAnimationPage_link = MapSelectPage.xpath('//li[@class="nextArea popupBtn"]//span[@class="prm_href"]/text()')[0]
  except IndexError:
    # no next area is found
    questItem_list = MapSelectPage.xpath('//li[@class="clearArea popupBtn"]//span[@class="prm_item_path"]/text()')
    for questItem in questItem_list:
      if questItem.find('question') > 0:
        nextQuestIndex = questItem_list.index(questItem)
        break
    QuestAnimationPage_link = MapSelectPage.xpath('//li[@class="clearArea popupBtn"]//span[@class="prm_href"]/text()')[nextQuestIndex]
  
  # get quest content
  QuestAnimationPage = ange_request(QuestAnimationPage_link)
  nextUrl = QuestAnimationPage.xpath('//span[@id="nextUrl"]/text()')[0]
  questAction_list = QuestAnimationPage.xpath('//span[@id="action"]/span/text()')
  print questAction_list
  
  # decide to do quest or not
  doFlag = True
  if (len([i for i in TARGET_ACTION_LIST if i in questAction_list]) > 0) or (len(questAction_list) <= int(config.get('ange', 'QUEST_ACTION_MAX'))):
    nextUrl += '&qpc=%s' % (len(questAction_list))
  else:
    questStep = 0
    questAction_list.reverse()
    while(len(questAction_list) > 0) and (questAction_list.pop() in ['b', 'c']):
      questStep += 1
    nextUrl += '&qrdctf=my&qpc=%s' % (questStep)
    if questStep == 0:
      doFlag = False
  ange_request(nextUrl)
  return doFlag

def doEvent():
  ''' type 1: delicated page to event stage page
  ange_MyPage()
  EventTopPage_link = '/ange/raid/RaidEventTopPage;jsessionid=%s' % (_jsessionid)
  EventTopPage = ange_request(EventTopPage_link)
  
  # find stage link from event top page
  MapSelectPage_link = re.findall('href=\"(.*MapSelectPage.*)\" ', etree.tostring(EventTopPage))[0]
  '''
  
  ''' type 2: additional link in stage selection '''
  MyPage = ange_MyPage()
  StageSelectPage_link = re.findall('href=\"(.*StageSelectPage.*)\" ', etree.tostring(MyPage))[1]
  
  # find map from stage
  StageSelectPage = ange_request(StageSelectPage_link)
  MapSelectPage_link = re.findall('href=\"(.*MapSelectPage.*)\" ', etree.tostring(StageSelectPage))[-2]
  ''' type 2 ends '''
    
  # find next area in map
  MapSelectPage = ange_request(MapSelectPage_link)
  try:
    # look for next area
    QuestAnimationPage_link = MapSelectPage.xpath('//li[@class="nextArea popupBtn"]//span[@class="prm_href"]/text()')[0]
  except IndexError:
    # no next area is found
    questItem_list = MapSelectPage.xpath('//li[@class="clearArea popupBtn"]//span[@class="prm_item_path"]/text()')
    for questItem in questItem_list:
      if questItem.find('question') > 0:
        nextQuestIndex = questItem_list.index(questItem)
        break
    QuestAnimationPage_link = MapSelectPage.xpath('//li[@class="clearArea popupBtn"]//span[@class="prm_href"]/text()')[nextQuestIndex]
  
  # get quest content
  QuestAnimationPage = ange_request(QuestAnimationPage_link)
  nextUrl = QuestAnimationPage.xpath('//span[@id="nextUrl"]/text()')[0]
  questAction_list = QuestAnimationPage.xpath('//span[@id="action"]/span/text()')
  print questAction_list
  
  # decide to do quest or not
  doFlag = True
  if (len([i for i in TARGET_ACTION_LIST if i in questAction_list]) > 0) or (len(questAction_list) <= int(config.get('ange', 'QUEST_ACTION_MAX'))):
    nextUrl += '&qpc=%s' % (len(questAction_list))
  else:
    questStep = 0
    questAction_list.reverse()
    while(len(questAction_list) > 0) and (questAction_list.pop() in ['b', 'c']):
      questStep += 1
    nextUrl += '&qrdctf=my&qpc=%s' % (questStep)
    if questStep == 0:
      doFlag = False
  ange_request(nextUrl)
  return doFlag

def doRaid():
  # find raid link from MyPage
  MyPage = ange_MyPage()
  RaidTopPage_link = MyPage.xpath('//div[@id="attention"]//li[@id="bossAt"]/a/@href')[0]
  RaidTopPage = ange_request(RaidTopPage_link)
  
  # do nothing if goes to RaidResultWinPage
  if RaidTopPage.xpath('//p[@id="touch_screen"]/text()'):
    return
  
  # call for help if possible
  RaidSeekHelpRedirectPage_link = re.findall('href=\"(.*RaidSeekHelpRedirectPage.*)\" ', etree.tostring(RaidTopPage))
  if RaidSeekHelpRedirectPage_link:
    RaidSeekHelpRedirectPage = ange_request(RaidSeekHelpRedirectPage_link[0])
  
  # find 5 units to fight
  fightUnit_list = RaidTopPage.xpath('//div[@id="prm_border_infos"]/span/text()')
  fightUnit = []
  fightBP = 0
  for i in range(int(config.get('ange', 'RAID_FIGHT_UNIT'))):
    fightUnit.append(fightUnit_list[i].split(',')[0])
    fightBP += int(fightUnit_list[i].split(',')[1])
    if int(fightUnit_list[i].split(',')[2]) == 0:
      # do recover for any dead
      fightBP += 9999
  
  # recover bp if not enough
  if _bp < fightBP:
    Hospital_link = re.findall('href=\"(.*RaidRepairPodInRedirectPage.*)\" ', etree.tostring(RaidTopPage))[0]
    ange_request(Hospital_link)
    time.sleep(3*60+5) # sleep for 3 minutes (plus 5 sec)
    Hospital_link = re.findall('href=\"(.*RaidRepairPodOutRedirectPage.*)\" ', etree.tostring(RaidTopPage))[0]
    ange_request(Hospital_link)
    return ange_MyPage()
  
  # go for battle
  RaidBattleRedirectPage_link = RaidTopPage.xpath('//span[@id="battleUrl"]/text()')[0]
  RaidBattleRedirectPage_link += '?ucid=%s' % (','.join(fightUnit))
  ange_request(RaidBattleRedirectPage_link)
  return ange_MyPage()

def doHelp():
  # find help link from MyPage
  MyPage = ange_MyPage()
  RaidSeekHelpListPage_link = MyPage.xpath('//div[@id="attention"]//li[@id="helpAt"]/a/@href')
  if RaidSeekHelpListPage_link:
    RaidSeekHelpListPage = ange_request(RaidSeekHelpListPage_link[0])
  else:
    return ange_MyPage()
  
  # help first
  RaidHelpOutRedirectPage_link = RaidSeekHelpListPage.xpath('//div[@id="RaidSeekHelpListPage"]//div[@class="btnArea"]/a/@href')
  if RaidHelpOutRedirectPage_link:
    RaidHelpOutRedirectPage = ange_request(RaidHelpOutRedirectPage_link[0])
  else:
    return ange_MyPage()
  
def doCombatHospital():
  Hospital_link = '/ange/combat/RepairPodInRedirectPage;jsessionid=%s' % (_jsessionid)
  ange_request(Hospital_link)
  time.sleep(3*60+5) # sleep for 3 minutes (plus 5 sec)
  Hospital_link = '/ange/combat/RepairPodOutRedirectPage;jsessionid=%s' % (_jsessionid)
  ange_request(Hospital_link)
  return

def doCombatPickUnit(unitList, pickNumber):
  '''
    unit list format:
      [
        id cost nowHp maxHp
        "95858532,13,0,16173",
        "94474953,14,0,17210"
      ]
    return unit in list if can do battle
    return None if cannot battle
  '''
  fightUnit = []
  fightBP = 0
  for unit in unitList:
    # check hp
    if int(unit.split(',')[2]) == 0:
      continue
    fightUnit.append(unit.split(',')[0])
    fightBP += int(unit.split(',')[1])
    if len(fightUnit) >= int(pickNumber):
      break

  if len(fightUnit) < int(pickNumber):
    # not enough unit
    return None
  if int(_bp) < int(fightBP):
    # not enough bp
    return None
  return fightUnit

def receiveItem():
  PresentListItemPage_link = '/ange/user/PresentListItemPage;jsessionid=%s' % (_jsessionid)
  PresentListItemPage = ange_request(PresentListItemPage_link)
  presentCount = int(re.search('(\d+)', PresentListItemPage.xpath('//div[@class="tabDiv"]//span[@id="presentTotalNum"]/text()')[0]).group(1))
  collectCount = 0
  while presentCount > 0:
    PresentListItemPage_link = '/ange/user/PresentListItemPage;jsessionid=%s?psallitm=true' % (_jsessionid)
    PresentListItemPage = ange_request(PresentListItemPage_link)
    presentCount = int(re.search('(\d+)', PresentListItemPage.xpath('//div[@class="tabDiv"]//span[@id="presentTotalNum"]/text()')[0]).group(1))
    collectCount += 1
  return '%s pages collected' % (collectCount)

def smartCombat():
  ange_MyPage()
  if int(config.get('ange', 'DO_COMBAT')) != 2:
    return 'SMART_COMBAT FLAG is off'
  while _clanBattle is True:
    doSmartCombat()
    ange_MyPage()
    time.sleep(10)
  return 'battle ended'

def doSmartCombat():
  ange_MyPage()
  CombatTopPage_link = '/ange/combat/CombatTopPage;jsessionid=%s' % (_jsessionid)
  CombatTopPage = ange_request(CombatTopPage_link)
  CombatMainPage_link = '/ange/combat/CombatMainPage;jsessionid=%s?historyBack_deny=1' % (_jsessionid)
  CombatMainPage = ange_request(CombatMainPage_link)
  comboCount  = int(CombatMainPage.xpath('//span[@id="prm_combo_num"]/text()')[0])
  comboMyself = int(CombatMainPage.xpath('//span[@id="prm_is_combo_myself"]/text()')[0])
  comboTime   = int(CombatMainPage.xpath('//span[@id="prm_combo_chance_time"]/text()')[0])
  print "combo: %s/%s" % (comboCount, comboTime)
  print "bp: %s/%s" % (_bp, _bp_max)
  print "lastAttack: %s" % comboMyself
  # decicde to battle or not
  if (comboMyself == 0) or (comboTime == 0):
    print "battle! (combo:%s)" % (comboCount)
    fightUnit_list = CombatMainPage.xpath('//div[@id="prm_border_infos"]/span/text()')
    print "\nunit:"
    print "\n".join(fightUnit_list)
    fightingUnit   = doCombatPickUnit(fightUnit_list, 1)
    if fightingUnit is None:
      print "no one can fight!"
      doCombatHospital()
      return False
    CombatRedirectPage_link = '/ange/combat/CombatRedirectPage;jsessionid=%s?historyBack_deny=1&ucid=%s' % (_jsessionid, ','.join(fightingUnit))
    CombatRedirectPage = ange_request(CombatRedirectPage_link)
    return True
  
  if (comboTime < 240) and (int(_bp) < int(_bp_max)):
    # no one wants to fight
    doCombatHospital()
  
  return False
  

def doCombat():
  ange_MyPage()
  if _clanBattle is False:
    return 'not in clan battle time'
  if int(config.get('ange', 'DO_COMBAT')) != 1:
    return 'DO_COMBAT FLAG is off'

  # battle 3 times
  CombatTopPage_link = '/ange/combat/CombatTopPage;jsessionid=%s' % (_jsessionid)
  CombatTopPage = ange_request(CombatTopPage_link)
  for i in range(3):
    CombatMainPage_link = '/ange/combat/CombatMainPage;jsessionid=%s?historyBack_deny=1' % (_jsessionid)
    CombatMainPage = ange_request(CombatMainPage_link)
    
    # pick unit to combat
    fightUnit_list = CombatMainPage.xpath('//div[@id="prm_border_infos"]/span/text()')
    fightingUnit = doCombatPickUnit(fightUnit_list, 1)
    CombatRedirectPage_link = '/ange/combat/CombatRedirectPage;jsessionid=%s?historyBack_deny=1&ucid=%s' % (_jsessionid, ','.join(fightingUnit))
    CombatRedirectPage = ange_request(CombatRedirectPage_link)
  return '3 battle ends'

def status():
  ange_MyPage()
  commandString = 'ps aux | grep "ange.py %s auto" | wc -l' % (ange_botName)
  botDead = True if int(os.popen(commandString).read()) < 3 else False
  #logging.debug('%3s/%3s/%4s/%s %s' % (_sp, _bp, (_exp_max - _exp), _raidBoss, "(Stopped)" if botDead else ""))
  print('%3s/%3s/%5s/%s %s' % (_sp, _bp, (_exp_max - _exp), _raidBoss, "(Stopped)" if botDead else ""))
  return '%3s/%3s/%5s/%s %s' % (_sp, _bp, (_exp_max - _exp), _raidBoss, "(Stopped)" if botDead else "")

def quest(adam=True):
  while doQuest(adam) is False:
    pass
  return status()

def adam():
  while doQuest(adam=True) is False:
    pass
  return status()

def event():
  while doEvent() is False:
    pass
  return status()

def auto():
  while 1:
    try:
      ange_MyPage()
      print '%3s/%3s/%4s/%s/%s' % (_sp, _bp, (_exp_max - _exp), _raidBoss, _clanBattle)
      if _sp < 0:
        # first init
        ange_MyPage()
      elif _raidBoss and not _clanBattle:
        doRaid()
      elif not _raidBoss and _sp > int(config.get('ange', 'QUEST_SP_MIN')) and int(config.get('ange', 'DO_EVENT')) == 1:
        # do event only for specified user
        doEvent()
      elif not _raidBoss and _sp > int(config.get('ange', 'QUEST_SP_MIN')):
        # do quest only if sp is high
        quest(adam=True)
      elif _helpBoss and not _clanBattle and int(config.get('ange', 'DO_HELP')) == 1:
        doHelp()
      elif _clanBattle and int(config.get('ange', 'DO_COMBAT')) == 2:
        doSmartCombat()
      else:
        time.sleep(1 * 60)
    except KeyboardInterrupt:
      sys.exit(1)
    except:
      time.sleep(5 * 60)

def execution(configFile, execFunc):
  global config
  config = SafeConfigParser()
  config.read(configFile)

  global ange_botName
  ange_botName = configFile.split('/')[0]
  
  # file logger
  log_fh = SingleLogHandler.SingleLogHandler('%s/log' % (ange_botName))
  log_fh.setLevel(logging.INFO)
  log.addHandler(log_fh)
  
  global ange_header
  ange_header = {
    "Host": "web.ange-app.com",
    "Accept-Language": "zh-tw",
    "X-iOS-WebView-Response-Check": "1",
    "Accept-Encoding": "gzip, deflate",
    "F4S_IOS_NOAHID": "0",
    "F4S_DL_VERSION": config.get('ange', 'F4S_DL_VERSION'),
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 8_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Mobile/12B411",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "F4S_IOS_USER_ID": config.get('ange', 'F4S_IOS_USER_ID'),
    "F4S_CLIENT_VER": "1.0.8",
    "Connection": "keep-alive",
    "F4S_IOS_PLATFORM": "iPhone5,2",
  }
    
  func = getattr(sys.modules[__name__], execFunc)
  return func()


if __name__ == '__main__':
  if len(sys.argv) < 3:
    print 'Usage: %s [alias] [command]' % (sys.argv[0])
    sys.exit(1)
    
  if len(sys.argv) == 3:
    if sys.argv[1] == 'all':
      for botName in [name for name in os.listdir(os.getcwd()) if os.path.isdir(name)]:
        print "\n%s" % (botName)
        execution('%s/ange.conf' % (botName), sys.argv[2])
    else:
      execution('%s/ange.conf' % (sys.argv[1]), sys.argv[2])
