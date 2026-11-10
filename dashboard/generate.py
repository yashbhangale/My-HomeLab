"""Generate Homepage and Gatus configuration; no credentials belong in this file."""
from pathlib import Path
import yaml
ROOT = Path(__file__).parent
PROM = 'http://monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090'
def metric(label, query, kind='number', suffix=None):
    fmt = {'type': kind}
    if kind == 'number': fmt['options'] = {'maximumFractionDigits': 1}
    if suffix: fmt['suffix'] = suffix
    return {'label': label, 'query': query, 'format': fmt}
def telemetry(name, icon, metrics, href='https://grafana.yashbhangale.site'):
    return {name: {'icon': icon, 'href': href, 'description': 'Live from Prometheus · refreshes every 15 seconds', 'widget': {'type': 'prometheusmetric', 'url': PROM, 'refreshInterval': 15000, 'metrics': metrics}}}
# name, namespace, public subdomain, icon, description, internal origin, pod selector
APPS = [
 ('Jellyfin','jellyfin','jellyfin','jellyfin.svg','Movies, music & your media library','http://jellyfin.jellyfin:8096','app=jellyfin'),
 ('Kavita','kavita','kavita','kavita.svg','Books, comics & reading','http://kavita.kavita:5000','app=kavita'),
 ('qBittorrent','qbittorrent','torrent','qbittorrent.svg','Downloads & transfer queue','http://qbittorrent.qbittorrent:8080','app=qbittorrent'),
 ('Obsidian','obsidian','obsidian','obsidian.svg','Your connected notes & knowledge','https://obsidian.yashbhangale.site','app=obsidian'),
 ('Nextcloud','nextcloud','nextcloud','nextcloud.svg','Personal files & collaboration','http://nextcloud.nextcloud:8080',''),
 ('Filebrowser','filebrowser','files','filebrowser.svg','Browse & organize shared storage','http://filebrowser.filebrowser:80','app=filebrowser'),
 ('Paperless','paperless','paperless','paperless-ngx.svg','Document archive & OCR','http://paperless.paperless:8000','app=paperless'),
 ('Open WebUI','openwebui','openui','open-webui.svg','Local models & AI conversations','http://openwebui-open-webui.openwebui:80',''),
 ('Home Assistant','homeassistant','ha','home-assistant.svg','Home automation & devices','http://homeassistant.homeassistant:8123','app=homeassistant'),
 ('Kasm','kasm','kasm','kasm.svg','Your browser-based desktop','https://kasm.kasm:443','app=kasm'),
 ('Browser terminal','wetty','ssh','terminal.svg','SSH terminal in your browser','http://wetty.wetty:3000','app=wetty'),
 ('Supabase','supabase','sb','supabase.svg','Database, auth, storage & APIs','http://supabase-supabase-kong.supabase:8000',''),
 ('Argo CD','argocd','argocd','argo-cd.svg','GitOps deployments & application health','http://argocd-server.argocd:80',''),
 ('Grafana','monitoring','grafana','grafana.svg','Resource trends, logs & detailed dashboards','http://monitoring-grafana.monitoring:80','app.kubernetes.io/name=grafana'),
]
def app(a):
    name, ns, sub, icon, desc, origin, selector = a
    d = {'icon': icon, 'href': f'https://{sub}.yashbhangale.site', 'description': desc, 'namespace': ns, 'app': ns, 'podSelector': selector, 'showStats': True}
    # Obsidian's namespace intentionally admits only its own tunnel and Traefik.
    if name not in ('Obsidian','Kasm','Supabase'): d['siteMonitor'] = 'https://nextcloud.yashbhangale.site/status.php' if name == 'Nextcloud' else origin
    return {name:d}
metrics = [
 telemetry('Compute','mdi-chip',[
  metric('CPU', '100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))',suffix='%'),
  metric('Memory', '100 * (1 - sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes))',suffix='%'),
  metric('CPU temp', 'max(node_hwmon_temp_celsius{chip="pci0000:00_0000:00:18_3"})',suffix='°C'),
  metric('Uptime','time() - max(node_boot_time_seconds)','duration')]),
 telemetry('Storage','mdi-harddisk',[
  metric('Root used','100 * (1 - sum(node_filesystem_avail_bytes{mountpoint="/",fstype="ext4"}) / sum(node_filesystem_size_bytes{mountpoint="/",fstype="ext4"}))',suffix='%'),
  metric('Root free','sum(node_filesystem_avail_bytes{mountpoint="/",fstype="ext4"})','bytes'),
  metric('Home used','100 * (1 - sum(node_filesystem_avail_bytes{mountpoint="/home",fstype="ext4"}) / sum(node_filesystem_size_bytes{mountpoint="/home",fstype="ext4"}))',suffix='%'),
  metric('Home free','sum(node_filesystem_avail_bytes{mountpoint="/home",fstype="ext4"})','bytes')]),
 telemetry('Network & power','mdi-access-point-network',[
  metric('Download','sum(rate(node_network_receive_bytes_total{device="wlp4s0"}[5m]))','byterate'),
  metric('Upload','sum(rate(node_network_transmit_bytes_total{device="wlp4s0"}[5m]))','byterate'),
  metric('Battery','max(node_power_supply_capacity{power_supply="BAT0"})',suffix='%'),
  metric('AC online','max(node_power_supply_online{power_supply="ADP0"})')]),
 telemetry('Cluster health','kubernetes.svg',[
  metric('Pods ready','sum(kube_pod_status_ready{condition="true"})'),
  metric('Not ready','sum(kube_pod_status_ready{condition="false"})'),
  metric('Restarts / 1h','sum(increase(kube_pod_container_status_restarts_total[1h])) or vector(0)'),
  metric('Firing alerts','count(ALERTS{alertstate="firing",alertname!="Watchdog"}) or vector(0)')], 'https://grafana.yashbhangale.site/alerting/list'),
]
services = [
 {'Live telemetry':metrics},
 {'Media & downloads':[app(a) for a in APPS[:3]]},
 {'Knowledge & files':[app(a) for a in APPS[3:7]]},
 {'Apps & workspaces':[app(a) for a in APPS[7:12]]},
 {'Operations':[
  {'Uptime history': {'icon':'gatus.svg','href':'https://status.yashbhangale.site','description':'Availability, latency & persistent check history','widget':{'type':'gatus','url':'http://127.0.0.1:8081'}}},
  app(APPS[12]),app(APPS[13]),
  {'Prometheus': {'icon':'prometheus.svg','href':'https://grafana.yashbhangale.site/explore','description':'Scrape health & time-series metrics','namespace':'monitoring','app':'prometheus','podSelector':'app.kubernetes.io/name=prometheus','showStats':True,'widget':{'type':'prometheus','url':PROM}}},
  {'Cloudflare tunnels': {'icon':'cloudflare.svg','href':'https://dash.cloudflare.com','description':'All in-cluster tunnel connectors','widget':{'type':'prometheusmetric','url':PROM,'metrics':[
   metric('Ready','sum(kube_pod_status_ready{namespace=~"cloudflared|obsidian|dashboard",pod=~".*tunnel.*|cloudflared-.*",condition="true"})'),
   metric('Not ready','sum(kube_pod_status_ready{namespace=~"cloudflared|obsidian|dashboard",pod=~".*tunnel.*|cloudflared-.*",condition="false"}) or vector(0)')]}}},
  {'Platform services':{'icon':'kubernetes.svg','href':'https://grafana.yashbhangale.site','description':'DNS, networking, storage & monitoring','namespace':'kube-system','app':'kube-system','podSelector':'','showStats':True}},
 ]},
]
settings={'title':"Yash's Homelab",'description':'One place for your applications, resources and uptime.','theme':'dark','color':'slate','headerStyle':'clean','statusStyle':'dot','showStats':True,'hideVersion':False,'disableUpdateCheck':True,'useEqualHeights':True,'target':'_blank','quicklaunch':{'searchDescriptions':True,'hideInternetSearch':True,'hideVisitURL':True},'layout':{
 'Live telemetry':{'style':'row','columns':4},
 'Media & downloads':{'style':'column'},
 'Knowledge & files':{'style':'column'},
 'Apps & workspaces':{'style':'column'},
 'Operations':{'style':'row','columns':3},
}}
widgets=[{'greeting':{'text':"Yash's Homelab",'text_size':'2xl'}},{'kubernetes':{'cluster':{'show':True,'cpu':True,'memory':True,'showLabel':True,'label':'K3s · boii'},'nodes':{'show':False}}},{'datetime':{'text_size':'md','format':{'dateStyle':'medium','timeStyle':'short','hour12':True}}}]
endpoints=[]
for a in APPS:
 name,ns,sub,icon,desc,origin,selector=a
 cond=['[STATUS] >= 200','[STATUS] < 400']
 if name in ('Obsidian','Supabase'):cond=['[STATUS] == 401']
 e={'name':name,'group':'Applications','url':origin,'interval':'60s','conditions':cond,'client':{'timeout':'10s'}}
 if name=='Nextcloud':e['url']='https://nextcloud.yashbhangale.site/status.php'
 if name=='Kasm':e['client']['insecure']=True
 if name=='Argo CD':e['client']['insecure']=True
 endpoints.append(e)
for name,url in [('Prometheus',PROM+'/-/ready'),('Alertmanager','http://monitoring-kube-prometheus-alertmanager.monitoring:9093/-/ready'),('CoreDNS','tcp://kube-dns.kube-system:53'),('Supabase Postgres','tcp://supabase-supabase-db.supabase:5432'),('Open WebUI Redis','tcp://openwebui-open-webui-redis.openwebui:6379')]:
 endpoints.append({'name':name,'group':'Infrastructure','url':url,'interval':'60s','conditions':['[CONNECTED] == true'] if url.startswith('tcp:') else ['[STATUS] == 200'],'client':{'timeout':'10s'}})
gatus={'web':{'port':8081},'metrics':True,'storage':{'type':'sqlite','path':'/data/gatus.db','maximum-number-of-results':1440,'maximum-number-of-events':100},'ui':{'title':"Yash's Homelab · Uptime",'description':'Live service checks. History begins when this monitor was deployed.','default-sort-by':'group','default-group':'Applications'},'endpoints':endpoints}
css='''/* Preserve Homepage's native components and responsive layout. */
:root { color-scheme: dark; }
#page_container { max-width: 1600px; margin-inline: auto; }
.service-group-name { font-weight: 650; letter-spacing: -0.015em; }
.service-description { line-height: 1.5; }
a:focus-visible, button:focus-visible { outline: 2px solid #67e8f9; outline-offset: 4px; }
::selection { background: #155e75; color: #ecfeff; }
'''
data={'settings.yaml':yaml.safe_dump(settings,sort_keys=False,allow_unicode=True),'services.yaml':yaml.safe_dump(services,sort_keys=False,allow_unicode=True),'widgets.yaml':yaml.safe_dump(widgets,sort_keys=False,allow_unicode=True),'kubernetes.yaml':yaml.safe_dump({'mode':'cluster','ingress':True}),'bookmarks.yaml':'[]\n','docker.yaml':'{}\n','custom.css':css,'custom.js':'','gatus.yaml':yaml.safe_dump(gatus,sort_keys=False,allow_unicode=True)}
config={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'homepage-config','namespace':'dashboard'},'data':data}
(ROOT/'config.yaml').write_text(yaml.safe_dump(config,sort_keys=False,allow_unicode=True))
print(f'Generated {len(APPS)} application cards, {len(endpoints)} health checks and {sum(len(list(c.values())[0]["widget"]["metrics"]) for c in metrics)} resource metrics.')
if __name__=='__main__':pass

# Coupling config changes to this deployment prevents stale seed files under GitOps.
app_file = ROOT / 'app.yaml'
if app_file.exists():
    import hashlib, re
    digest = hashlib.sha256((ROOT/'config.yaml').read_bytes()).hexdigest()[:16]
    app_file.write_text(re.sub(r'(dashboard.homelab/config-revision: )"[^"]+"',r'\1"'+digest+'"',app_file.read_text()))
