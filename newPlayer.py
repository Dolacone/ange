import httplib, gzip, re, time, sys, os, glob
from StringIO import StringIO
from lxml.html.clean import Cleaner
from lxml import etree
from ConfigParser import SafeConfigParser

sys_config = SafeConfigParser()
sys_config.read('ange.conf')

config = None
ange_header = None

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
  print path
    
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
  
_sp = -1
_sp_max = -1
_bp = -1
_bp_max = -1
_exp = -1
_exp_max = -1
_jsessionid='9708A0E605F8A5E6ED0418925C0BBD7B'
TARGET_ACTION_LIST = ['e', 'f'] # do action if e(quest item) and f(sync up) occurs
_raidBoss = False
_helpBoss = False
_clanBattle = False

def ange_MyPage():
  global _sp, _sp_max, _bp, _bp_max, _exp, _exp_max, _jsessionid, _raidBoss, _helpBoss, _clanBattle
  MyPage = ange_request('/ange/user/MyPage;jsessionid=%s.avmap14' % (_jsessionid))
  _sp      = int(MyPage.xpath("//span[@id='prm_head_ap']/text()")[0])
  _sp_max  = int(MyPage.xpath("//span[@id='prm_head_ap_max']/text()")[0])
  _bp      = int(MyPage.xpath("//span[@id='prm_head_bp']/text()")[0])
  _bp_max  = int(MyPage.xpath("//span[@id='prm_head_bp_max']/text()")[0])
  _exp     = int(MyPage.xpath("//span[@id='prm_head_exp']/text()")[0])
  _exp_max = int(MyPage.xpath("//span[@id='prm_head_exp_max']/text()")[0])
  _jsessionid = re.findall('jsessionid=(\w*)\.',etree.tostring(MyPage))[0]
  _raidBoss = True if MyPage.xpath('//div[@id="attention"]//li[@id="bossAt"]/a/@href') else False
  _helpBoss = True if MyPage.xpath('//div[@id="attention"]//li[@id="helpAt"]/a/@href') else False
  _clanBattle = True if MyPage.xpath('//p[@class="claconLink"]//a/@href') else False
  return MyPage
  
def newPlayer():
  previous_content = None
  while ange_request('/ange/') != previous_content:
    pass
  return

def newCombat():
  ange_request('/ange/user/MyPage;jsessionid=%s' % (_jsessionid))
  ange_request('/ange/combat/CombatTopPage;jsessionid=%s' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain01Page;jsessionid=%s' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain02Page;jsessionid=%s' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain03Page;jsessionid=%s?&historyBack_deny=1' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain04Page;jsessionid=%s?&historyBack_deny=1' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain05Page;jsessionid=%s?&historyBack_deny=1' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain06Page;jsessionid=%s?&historyBack_deny=1' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain07Page;jsessionid=%s' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain08Page;jsessionid=%s?&historyBack_deny=1' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain09Page;jsessionid=%s?&historyBack_deny=1' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain10Page;jsessionid=%s' % (_jsessionid))
  ange_request('/ange/tutorial/TutorialCombatMain11Page;jsessionid=%s' % (_jsessionid))

  
def setHeader():
  global ange_header
  ange_header = {
    "Host": "web.ange-app.com",
    "Accept-Language": "zh-tw",
    "X-iOS-WebView-Response-Check": "1",
    "Accept-Encoding": "gzip, deflate",
    "F4S_IOS_NOAHID": "0",
    "F4S_DL_VERSION": sys_config.get('client', 'f4s_dl_version'),
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 8_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Mobile/12B411",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "F4S_IOS_USER_ID": config.get('ange', 'F4S_IOS_USER_ID'),
    "F4S_CLIENT_VER": "1.0.8",
    "Connection": "keep-alive",
    "F4S_IOS_PLATFORM": "iPhone5,2",
  }
  
def setConfig(configFile):
  global config
  config = SafeConfigParser()
  config.read(configFile)

  
def execution(configFile, execFunc):
  setConfig(configFile)
  setHeader()
  
  global ange_botName
  ange_botName = configFile.split('/')[0]
      
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