importasyncio
importjson
importlogging
importtime
fromtypingimportAny

logger=logging.getLogger(__name__)


classStratumServer:
"""AsynchronerStratumV1MiningServermitClient-VerwaltungundHealth-Check."""

def__init__(self,host:str,port:int)->None:
self.host=host
self.port=port
self._server:asyncio.Server|None=None
self.active_connections=0
self.start_time:float|None=None
self._is_running=False
self._jobs:dict[str,dict[str,Any]]={}

asyncdefstart(self)->None:
"""StartetdenTCP-Stratum-Server."""
self._server=awaitasyncio.start_server(
self.handle_client,self.host,self.port
)
self._is_running=True
self.start_time=time.time()

#Portauslesen,fallsport=0(dynamischerPortfürTests)gewähltwurde
ifself._server.sockets:
self.port=self._server.sockets[0].getsockname()[1]
logger.info("StratumServergestartetauf%s:%d",self.host,self.port)

asyncdefstop(self)->None:
"""StopptdenServerundschließtalleVerbindungensauber."""
self._is_running=False
ifself._server:
self._server.close()
awaitself._server.wait_closed()
self._server=None
logger.info("StratumServergestoppt.")

defregister_job(self,job_id:str,job_data:dict[str,Any])->None:
"""RegistrierteinenneuenMining-JobimServer."""
self._jobs[job_id]=job_data
logger.info("Job%serfolgreichimServerregistriert.",job_id)

asyncdefhandle_client(
self,reader:asyncio.StreamReader,writer:asyncio.StreamWriter
)->None:
"""VerwalteteineeinzelneClient-VerbindungüberdasStratum-Protokoll."""
self.active_connections+=1#Zählererhöhen
peername=writer.get_extra_info("peername")
logger.info("NeuerClientverbunden:%s",peername)
try:
whileself._is_running:
data=awaitreader.readline()
ifnotdata:
break

message_str=data.decode("utf-8").strip()
ifnotmessage_str:
continue
try:
message=json.loads(message_str)
exceptjson.JSONDecodeError:
#JSON-Fehlerantwortsenden
error_resp={
"id":None,
"result":None,
"error":[-32700,"Parseerror:InvalidJSON",None],
}
writer.write((json.dumps(error_resp)+"\n").encode("utf-8"))
awaitwriter.drain()
continue
msg_id=message.get("id")
method=message.get("method")
#StratumSubscribebehandeln
ifmethod=="mining.subscribe":
response={
"id":msg_id,
"result":[
[
["mining.set_difficulty","subscription_id_1"],
["mining.notify","subscription_id_2"],
],
"extranonce1_hex",
4,
],
"error":None,
}
writer.write((json.dumps(response)+"\n").encode("utf-8"))
awaitwriter.drain()
except(ConnectionError,asyncio.CancelledError):
pass
finally:
self.active_connections-=1
logger.info("Client-Verbindunggetrennt:%s",peername)
writer.close()
awaitwriter.wait_closed()

defget_health_status(self)->dict[str,Any]:
"""GibtdenaktuellenGesundheits-undMetrikstatusdesServerszurück."""
uptime=time.time()-self.start_timeifself.start_timeelse0.0
return{
"status":"healthy"ifself._is_runningelse"stopped",
"is_running":self._is_running,
"active_connections":self.active_connections,
"uptime_seconds":round(uptime,2),
"host":self.host,
"port":self.port,
"registered_jobs_count":len(self._jobs),
}
