from fabric.api import *
from fabric.colors import *

env.user = 'ubuntu'
# env.hosts = ['col.walkerart.org',] #waiting for internal dns
env.hosts = ['ec2-23-20-45-108.compute-1.amazonaws.com',]
env.http_port = '8180'
project_dir = '/home/ubuntu/src/v2.0/'
minibuild_dir = '/home/ubuntu/src/minibuild/'
CSPACE_JEESERVER_HOME = '/usr/local/share/apache-tomcat-6.0.33'

def stop_server():
    "tomcat does not stop in time so we need to kill it"
    with settings(warn_only=True):
        run('source ~/.bashrc && ' + CSPACE_JEESERVER_HOME+'/bin/shutdown.sh -force', pty=False)
    pid = get_pid()
    if not pid:
        print(red("no java process found"))
        return
    puts(yellow("stopping pid " + pid))
    with settings(warn_only=True):
        run('kill -9 ' + pid)
    rm_pid()

def get_pid():
    pid = run("ps -C java | grep java | awk '{print$1}'",True)
    puts(green("pid = " + pid))
    return pid

def rm_pid():
    run('touch '+ CSPACE_JEESERVER_HOME +'/bin/tomcat.pid')
    run('rm '+ CSPACE_JEESERVER_HOME +'/bin/tomcat.pid')

def start_server():
    run('source ~/.bashrc && '+CSPACE_JEESERVER_HOME+'/bin/startup.sh', pty=False)
    get_pid()

def cat_log():
    run("tail "+CSPACE_JEESERVER_HOME+"/logs/catalina.out", pty=False)

def build():
    print( run('pwd', True))
    run('ant undeploy deploy', pty=False)

# @hosts('localhost')
def hit_init():
    env.cookie_file = "cookies.txt"
    env.login_userid = 'admin@walkerart.org'
    env.login_password = prompt("enter password for {}:".format(env.login_userid))
    local("""\
          wget -q --keep-session-cookies --save-cookies {cookie_file} \
          --post-data "userid={login_userid}&password={login_password}" \
          http://{host_string}:{http_port}/collectionspace/tenant/walkerart/login \
          -O /dev/null \
          """.format(**env))

    cookie = open(env.cookie_file).readlines().pop()
    if "CSPACESESSID" in cookie:
        print(green("logged in successfully"))
    else:
        print(red("not logged in! wrong password?"))
        return 

    local("""\
          wget --keep-session-cookies --load-cookies {cookie_file} \
          http://{host_string}:{http_port}/collectionspace/tenant/walkerart/init \
          -O - \
          """.format(**env))

    local('rm ' + env.cookie_file)


def git_pull():
    run('git pull origin custom')
        
def upgrade():
    "this is for deploying schema changes"
    with cd(project_dir):
        git_pull()
        stop_server()
        build()
        start_server()
        
def deploy(layer='application'):
    directory = "{path}/{layer}".\
                  format(path=minibuild_dir,  layer=layer)
    with cd(minibuild_dir):
        git_pull()
    stop_server()
    with cd(directory):
        build()
    start_server()
        
