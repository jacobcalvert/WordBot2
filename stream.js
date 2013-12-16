jQuery(document).ready(function(){
/*
 * Config section
 */
var DebugLevel= {"Info":0,"Warning":1,"Error":2,"Severe":3}
DEBUG_LEVEL = DebugLevel.Info;
WEBSOCKET_ADDRESS = "ws://172.22.114.128/ws";
RECONNECT_ON_LOST_CONNECTION = 0;
/*
 * End Config section
 */
function notify(obj)
{
    //eventually will be a popup or something
}
function WS_Opened()
{
    notify("!");
    log("Websocket called open.",DebugLevel.Info);
    WS_Req_Desc();
}
function WS_Closed()
{
    notify("!");
    log("WS closed",DebugLevel.Warning);
}
function WS_Msg(evt)
{
    jObj = JSON.parse(evt.data);
    log(jObj,DebugLevel.Info);
    $("#results").empty();
    app_str = "";
    str = "<div class='result_row_number'>Place</div><div class='result_row_left'>Word</div><div class='result_row_right'>Uses</div>";
    app_str+=str;
    for(i = 0; i<jObj.length; i++)
    {
        key = jObj[i][0];
        val = jObj[i][1];
        str = "<div class='result_row_number'>"+(1+i)+")</div><div class='result_row_left'>"+key+"</div><div class='result_row_right'>"+val+"</div>";
        app_str+=str;
    
    }
    $("#results").append(app_str);
}
function WS_Req_Desc()
{
    jObj = {"request":"DESC"};
    window.ws.send(JSON.stringify(jObj));
}
function WS_Req_Asc()
{
    jObj = {"request":"ASC"};
    window.ws.send(JSON.stringify(jObj));
}
function WS_Req_All()
{
    jObj = {"request":"ALL"};
    window.ws.send(JSON.stringify(jObj));
}


// logging stuff


function log(obj,level)
{
    if(level >= DEBUG_LEVEL)
    {
        console.log(obj);
    }
}
function init()
{
    window.ws = new WebSocket(WEBSOCKET_ADDRESS);
    window.ws.onopen = WS_Opened;
    window.ws.onclose = WS_Closed;
    window.ws.onmessage = WS_Msg;
    log("WS opened.", DebugLevel.Info);
    $("#desc").click(WS_Req_Desc);
    $("#asc").click(WS_Req_Asc);
    $("#all").click(WS_Req_All);
}
init();

});