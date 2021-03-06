from fabric.api import (puts,env,cd,settings,prompt,open_shell, hosts)
from fabric.api import local as wrapped_local
from fabric.api import run as wrapped_run
from fabric.colors import red,green,yellow,magenta
from lxml import objectify
from BeautifulSoup import BeautifulStoneSoup

env.user = 'ubuntu'
env.hosts = ['ec2-23-20-45-108.compute-1.amazonaws.com',]
env.http_port = '8180'
env.CSPACE_JEESERVER_HOME = '/usr/local/share/apache-tomcat-6.0.33'
env.service_identifier = 'wac-collectionspace'
env.tenant = 'walkerart'
env.login_userid = 'admin@walkerart.org'

project_dir = '/home/ubuntu/src/v2.0/'
minibuild_dir = '/home/ubuntu/src/minibuild/'

rrun   = lambda string,*args,**kwargs: wrapped_run(string.format(**env), *args,**kwargs)
llocal = lambda string,*args,**kwargs: wrapped_local(string.format(**env), *args,**kwargs)
        
def _login(func):
    "decorator which uses a session cookie"
    def logged_in(*args,**kwargs):
        _get_cookie()
        func(*args,**kwargs)
        llocal('rm ' + env.cookie_file)
    return logged_in
    
def stop_server():
    "runs shutdown.sh -force and kills tomcat"
    with settings(warn_only=True):
        rrun('source ~/.bashrc &&  {CSPACE_JEESERVER_HOME}/bin/shutdown.sh -force', pty=False)
    pid = get_pid()
    if not pid:
        print(red("no java process found"))
        return

    pids = pid.split('\r\n')
    if len(pids) > 1:
        puts(magenta("multiple pids found: " + ','.join(pids)))
        puts(magenta("kill them yourself (exit when done)"))
        open_shell()
    else:
        puts(yellow("stopping pid " + pid))
        with settings(warn_only=True):
            rrun('kill -9 ' + pid)
    rm_pid()

def get_pid():
    "pid of java program using unique identifier"
    pid = rrun("ps ww -C java | grep {service_identifier} | awk '{{print$1}}'",True)
    puts(green("pid = " + pid))
    return pid

def rm_pid():
    rrun('touch {CSPACE_JEESERVER_HOME}/bin/tomcat.pid')
    rrun('rm {CSPACE_JEESERVER_HOME}/bin/tomcat.pid')

def start_server():
    "start collectionspace"
    pid = get_pid()
    if pid:
        puts(yellow('server appears to be running; run stop_server first'))
        return 
    rrun('source ~/.bashrc && {CSPACE_JEESERVER_HOME}/bin/startup.sh -dservice.identifier={service_identifier}', pty=False)
    pid = get_pid()

def cat_log():
    "see tail of catalina.out"
    rrun("tail {CSPACE_JEESERVER_HOME}/logs/catalina.out", pty=False)

def _build():
    rrun('ant undeploy deploy', pty=False)

def _get_cookie():
    "login to collectionspace and GET tenant init to reload the configs"
    env.cookie_file = "cookies.txt"
    env.login_password = prompt("enter password for {}:".format(env.login_userid))
    llocal("""\
          wget -q --keep-session-cookies --save-cookies {cookie_file} \
          --post-data "userid={login_userid}&password={login_password}" \
          http://{host_string}:{http_port}/collectionspace/tenant/walkerart/login \
          -O /dev/null \
          """)

    cookie = open(env.cookie_file).readlines().pop()
    if "CSPACESESSID" in cookie:
        print(green("logged in successfully"))
    else:
        print(red("not logged in! wrong password?"))
        exit

@hosts('localhost')
def local_tenant_init():
    "shortcut of tenant_init for localhost"
    tenant_init()

@_login
def tenant_init():
    "hit tenant/{tenant}/init to reload configs"
    llocal("""\
          wget --keep-session-cookies --load-cookies {cookie_file} \
          http://{host_string}:{http_port}/collectionspace/tenant/{tenant}/init \
          -O - \
          """)

@hosts('localhost')
def local_init():
    "shortcut of auth_init for localhost"
    auth_init()

@_login
def auth_init():
    "hit authorities/initialise and authorities/vocab/initialize"
    llocal('wget  --keep-session-cookies --load-cookies {cookie_file} \
           http://{host_string}:{http_port}/collectionspace/tenant/{tenant}/authorities/initialise -O -')
    llocal('wget  --keep-session-cookies --load-cookies {cookie_file} \
           http://{host_string}:{http_port}/collectionspace/tenant/{tenant}/authorities/vocab/initialize -O - ')#!!z!!


def _git_pull():
    rrun('git pull origin custom')
        
def deploy(layer='application'):
    "pull updates from git origin and load 'em up"
    directory = "{path}/{layer}".\
                  format(path=minibuild_dir,  layer=layer)
    with cd(minibuild_dir):
        _git_pull()
    stop_server()
    with cd(directory):
        _build()
    start_server()


def get_authority(authority):
    "use the ?authorities naming style; so org for orgauthorities and person for personauthorities"
    env.authorities = authority + 'authorities'
    env.login_password = prompt("enter password for {}:".format(env.login_userid))
    llocal('wget --user={login_userid} --password={login_password} --keep-session-cookies \
           http://{host_string}:{http_port}/cspace-services/{authorities} -O authorities.xml ')

    string = open('authorities.xml').read()
    tree = objectify.fromstring(string)
    items = [(item.displayName,item.csid)  for item in tree.findall('list-item')]
    item = filter(lambda item: 'Test' not in str(item[0]), items)
    csid = item[0][1]
    _compose_post_data(authority)
    _post_item_to_authority(authority,csid)
    llocal('rm authorities.xml')
    llocal('rm {}.xml'.format(authority))


def _compose_post_data(authority):
    string = open('authority_template.xml').read()
    new_file = open(authority + '.xml', "w")
    env.doctype = authority
    env.schema_name = authority + 's_' + 'common'
    env.displayname = authority.capitalize()
    env.short_display_name = authority[:3]
    env.description = 'test authority'
    env.tenant_schema_name = authority + 's_' + env.tenant
    env.content = '<employer>Mr. Testy</employer> \
                   <assistant>Mr. Helper</assistant>'
    doc = string.format(**env)
    new_file.write(doc)
    new_file.close()


def _post_item_to_authority(authority,csid):
    "use the name of the xml file in this directory without the .xml"
    env.authorities = authority + 'authorities'
    env.authority = authority
    env.csid = csid
    response = llocal("curl -i -u {login_userid}:{login_password} -X POST -H \"Content-Type: application/xml\" \
           http://{host_string}:{http_port}/cspace-services/{authorities}/{csid}/items \
           -T {authority}.xml", True)
    tuples = filter(lambda t: ': ' in t, response.split('\r\n'))
    dd = dict(map(lambda string: tuple(string.split(': ')) , tuples))
    _view_item(dd['Location'])

def _view_item(location):
    env.location = location
    response = llocal("curl -i -u {login_userid}:{login_password} \
           {location} ", True)
    soup = BeautifulStoneSoup(response)
    print soup.prettify()