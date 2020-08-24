// REALTIME
var realtimeStartTime; //no change, input for jiandong function
var realtimeLoopNo=0; 
var realtimemodal_alert = document.getElementById('myModal_alert_4_minutes');
var realtime_interval;
var runrealtime;
var start_time;

$('#realtime').click(()=>{
    simulationMode=0;//realtime mode on
    realtimeLoopNo=0;
    runrealtime=true;
    simulationTimeInterval=15;
    document.getElementById("realtime").disabled = true;
    // document.getElementById("simulation").disabled = true;
    checkCountBoolean=true;
    if(runrealtime){
        realtimeInterval()
    }
});

function realtimeInterval(){
    start_time=new Date();
    realtimeStartTime=new Date();
    var countdownFlag=true; // true -> run
    var autosubmitFlag=true;
    console.log("开始");
    document.getElementById("count_down_text_2").style.display="block"; 
    realtime_interval = setInterval(function(){ 
        var elapsed_time = Date.now()-start_time;
        document.getElementById("simulation").innerHTML = (elapsed_time / 1000).toFixed(3);
        var min = Math.floor(((290000-elapsed_time)/ 1000).toFixed(0)/60); // 890000
        var sec = ((290000-elapsed_time)/ 1000).toFixed(0)-60*min; // 890000
        document.getElementById("count_down_text_2").innerHTML=min+":"+('0'+sec).slice(-2)+" left until this form will be submitted automatically.";
        // if(elapsed_time>830000&&elapsed_time<=890000){ // count down from 13'50''
        if(elapsed_time>230000&&elapsed_time<=290000){ // count down from 3'50''
            if(countdownFlag){
                countdownFlag=false;
                console.log("一分钟倒计时", elapsed_time);
                if(realtimemodal.style.display=="block"||realtimemodal_confirm.style.display=="block"){
                    realtimemodal_alert.style.display = "block";
                    var count=59;
                    var countDownInterval = setInterval(function(){
                        document.getElementById("count_down_text").innerHTML=count+" seconds left for change!";
                        count=count-1;
                        if (count<0) {
                            clearInterval(countDownInterval);
                        }
                    },1000);
                }
            }   
        // } else if(elapsed_time>890000&&elapsed_time<=900000){ // auto submit from 14'50''
        } else if(elapsed_time>290000&&elapsed_time<=300000){ // auto submit from 4'50''
            //auto submit
            if(autosubmitFlag){
                autosubmitFlag=false;
                console.log("自动提交 ", elapsed_time);
                document.getElementById("count_down_text_2").style.display="none";
                if(realtimemodal.style.display=="block"||realtimemodal_confirm.style.display=="block"){
        
                    updateConfirmList=[];
                    if(updateList.length!=0){
                        document.querySelectorAll('.realtime_select').forEach(function(element) {
                            var temp = updateList.find(x => x[1] === element.getAttribute('ganttid'));
                            updateConfirmList.push([element.getAttribute('ganttid'),element.selectedIndex+1,element.getAttribute('original-carousel'),temp[0],temp[4]]);
                        });
                    }
                    updateGantt(updateConfirmList,0);
                    realtimemodal_alert.style.display = "none";
                    realtimemodal_confirm.style.display = "none";
                    updateGanttPartTwo();
                    sendUpdatesNotSimulation(updateCSVList);
                    minuteLoadBigArmInit = jQuery.extend(true, {}, temp_minuteLoadBigArmInit);
                    calculateALLSTD(1,0);
                    realtimemodal.style.display = "none";
                } else{
                    console.log("已经提交");
                }
            }
        // } else if(elapsed_time>900000){ // at 15'
        } else if(elapsed_time>300000){ // at 5'
            clearInterval(realtime_interval);
            if(runrealtime){
                realtimeInterval()
            }
        }
    }, 100);
    getRealtimeDataNotSimulation();
    checkModalView(0);
}

function getRealtimeDataNotSimulation(){
    // get real time data
    var d=start_time; // starttime + 30 min, interval 5 min
    var timestamp=d.getFullYear()  + "-" + ("0"+(d.getMonth()+1)).slice(-2) +"-"+("0" + d.getDate()).slice(-2) + " " + ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2)+":00";
    var c=realtimeStartTime; // in minutes, start time 固定
    var starttime=c.getFullYear()  + "-" + ("0"+(c.getMonth()+1)).slice(-2) +"-"+("0" + c.getDate()).slice(-2) + " " + ("0" + c.getHours()).slice(-2) + ":" + ("0" + c.getMinutes()).slice(-2)+":00";

    $.ajax({
        method: 'POST',
        dataType: 'json',
        url: '/get_realtime',
        data: {
            starttime:starttime,
            date: timestamp,//date_str,
            load:JSON.stringify([1,2,3,4,5,6,7,8,9,10,11,12]),
            loopno:realtimeLoopNo,
            initialize: false
        },
        success: function (response) {
            if (!response.Error) {
                var rtdata =  adduniqueid(response.Details);
                console.log("get real time data",response);
                realtimeLoopNo++;
                compareData(rtdata);
            } else {
                alert(response.Msg+" real time data error in response");
                end_realtime()
            }
        },
        error: function (error) {
            alert(error.message+" real time data no data found in db");
            end_realtime()
        }
    })
}

function sendUpdatesNotSimulation(updateCSVList){
    $.ajax({
        method: 'POST',
        dataType: 'json',
        url: '/update_realtime',  
        data: {
            date: date_str,
            updateList:JSON.stringify(updateCSVList),
            initialize: false
        },
        success: function (response) {
            if (!response.Error) {
                console.log("get update csv response",response);
            } else {
                alert(response.Msg+" update CSV failed");
            }
        },
        error: function (error) {
            alert(error.message+" update CSV failed");
        }
    })
}

$('#close_realtime_alert').click(()=>{
    realtimemodal_alert.style.display = "none";
});

function end_realtime(){
    clearInterval(realtime_interval);
    checkCountBoolean=false;
    runrealtime=false;
}