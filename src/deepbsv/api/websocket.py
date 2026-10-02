importasyncio

importlogging

fromtypingimportAny

fromfastapiimportWebSocket

logger=logging.getLogger(__name__)

classConnectionManager:

"""VerwaltetaktiveWebSocket-VerbindungenfürdasEchtzeit-Dashboard."""

def__init__(self)->None:

self.active_connections:set[WebSocket]=set()

asyncdefconnect(self,websocket:WebSocket)->None:

awaitwebsocket.accept()

self.active_connections.add(websocket)

logger.info(

"NeuerWebSocket-Clientverbunden.AktiveVerbindungen:%d",

len(self.active_connections),

)

defdisconnect(self,websocket:WebSocket)->None:

self.active_connections.remove(websocket)

logger.info(

"WebSocket-Clientgetrennt.AktiveVerbindungen:%d",

len(self.active_connections),

)

asyncdefbroadcast(self,message:dict[str,Any])->None:

"""SendetDatenanalleverbundenenWeb-UI-Clients."""

ifnotself.active_connections:

return

disconnected=set()

forconnectioninself.active_connections:

try:

awaitconnection.send_json(message)

exceptExceptionase:#noqa:BLE001

logger.error("FehlerbeimSendenüberWebSocket:%s",e)

disconnected.add(connection)

#ToteVerbindungenaufräumen

forconnindisconnected:

self.active_connections.remove(conn)

manager=ConnectionManager()

asyncdefbackground_metrics_broadcaster()->None:

"""SimuliertoderholtperiodischLive-MetrikenundstreamtsieandasFrontend."""

whileTrue:

try:

payload:dict[str,Any]={

"type":"metrics_update",

"hashrate":0.0,

"active_miners":0,

"current_height":0,

}

awaitmanager.broadcast(payload)

exceptExceptionase:#noqa:BLE001

logger.error("FehlerimMetricsBroadcaster:%s",e)

awaitasyncio.sleep(2.0)
