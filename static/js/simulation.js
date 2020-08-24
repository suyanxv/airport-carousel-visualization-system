// SIMULATION
var realtimemodal = document.getElementById('myModal_realtime');
var realtimemodal_confirm = document.getElementById('myModal_realtime_confirm');
var realtimemodal_input = document.getElementById('myModal_simulation_input');
var simulationStartTime;
var simulationTimeInterval;
var currentSimulationTime;
var simulationMode=-1;
var checkCountBoolean = false;

/*
click on simulation button
*/
$('#simulation').click(()=>{
    simulationMode=1;
    realtimeLoopNo=0;
    runrealtime=true;
    checkCountBoolean=true;
    if(runrealtime){
        simulation();
    }
	document.querySelector("#operations").disabled = true;
});

/*
start simulation, input simulation start time and interval
*/
var simulation = function simulation(){
    realtimemodal_input.style.display='block';
    document.getElementById('simulation_start_time_date').innerHTML=date_str;
}

/*
click on simulation confirm button
*/
$('#confirm_simulation_input').click(()=>{
    simulationTimeInterval=document.getElementById('time-interval').value;
    simulationStartTime=document.getElementById('simulation-time-input').value;
    if(simulationTimeInterval!=null&&simulationStartTime!==null){
        start_time=new Date(date_str+" "+simulationStartTime+":00");
    } else{
        start_time=new Date(date_str+" 00:00:00");
    }
    console.log(currentSimulationTime,start_time);
    realtimemodal_input.style.display='none';
    document.getElementById("simulation").disabled = true;
    document.getElementById("realtime").disabled = true;
    getRealtimeData();
    var milliseconds=simulationTimeInterval*1000;
    setTimeout(function(){
        checkModalView(0);
    }, milliseconds);
});

/*
POST method to get real time simulation data
*/
function getRealtimeData(){
    var d=start_time;
    var olddata = {};
    var timestamp=d.getFullYear()  + "-" + ("0"+(d.getMonth()+1)).slice(-2) +"-"+("0" + d.getDate()).slice(-2) + " " + ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2)+":00";
    console.log(d, timestamp);
    $.ajax({
        method: 'POST',
        dataType: 'json',
        url: '/get_simulation',  
        data: {
            date: timestamp,//date_str,
            load:JSON.stringify(getMinuteLoad()),
            loopno:realtimeLoopNo,
            initialize: false
        },
        success: function (response) {
            if (!response.Error) {
                console.log("get real time data",response);
                if(start_time.getDate() > new Date(date_str).getDate()){ // new day
                    console.log("NEW DAY");
                    console.log("Before PUSH : ", data.length)
                    //data = data.concat(adduniqueid(response.All_Details))
                    data.push.apply(olddata, adduniqueid(response.All_Details)); // CSV problem here, data concat data cause double result.
                    console.log("After PUSH : ", data.length)
                } else{
                    data = adduniqueid(response.All_Details);
                    }
                var rtdata =  adduniqueid(response.Details);
                realtimeLoopNo++;
                compareData(rtdata);
            } else {
                console.log('get new date error!!',response)
                alert(response.Msg+" real time data error in response");
                end_realtime()
            }
        },
        /*Success: function (response) {
            if (!response.Error) {
                console.log("get real time data",response);
                if(start_time.getDate() > new Date(date_str).getDate()){ // new day
                    console.log("NEW DAY");
                    console.log("Before PUSH : ", data.length)
                    //data = data.concat(adduniqueid(response.All_Details))
                    data.push.apply(data, adduniqueid(response.All_Details)); // CSV problem here, data concat data
                    console.log("After PUSH : ", data.length)
                } else{
                    data = adduniqueid(response.All_Details);
                }
                var rtdata =  adduniqueid(response.Details);
                realtimeLoopNo++;
                compareData(rtdata);
            } else {
                console.log('get new date error!!',response)
                alert(response.Msg+" real time data error in response");
                end_realtime()
            }
        },*/
        error: function (error) {
            console.log('ajax get data error!!',error)
            alert(error.message+" real time data no data found in db");
            end_realtime()
        }
    })
    console.log("ajax done");
}

/*
POST method to send simulation update info back to backend csv
*/
function sendUpdates(updateCSVList){

    $.ajax({
        method: 'POST',
        dataType: 'json',
        url: '/update_simulation',  
        data: {
            date: date_str,
            updateList:JSON.stringify(updateCSVList),
            initialize: false
        },
        success: function (response) {
            if (!response.Error) {
                console.log("get update csv response",response);
                if(runrealtime){
                    start_time.setMinutes(start_time.getMinutes()+15)
                    getRealtimeData();

                    var milliseconds=simulationTimeInterval*1000;
                    setTimeout(function(){
                        checkModalView(0);
                    }, milliseconds);
                }
            } else {
                alert(response.Msg+" update CSV failed");
            }
        },
        error: function (error) {
            alert(error.message+" update CSV failed");
        }
    })
    
}

/*
find init plan data counterparts for realtime data, put into updateList
*/
var compareData = function compareData(rtdata){
    updateList=[];
    rtdata.forEach(function(value){
        var temp = gantt.isTaskExists(value.unique_id);
        if(temp==true){
            var gantttask = gantt.getTask(value.unique_id);
            var starttime = ultimateDateFormatter(value.STA,-2)
            var endtime = ultimateDateFormatter(value.STA)
            if((start_time>starttime)&&(endtime>starttime)&&(value.Allocation != parseInt(gantttask.dyn_belt,10))){ //dyn_belt
                console.log("TEST ", value.Allocation, parseInt(gantttask.dyn_belt,10));
                updateList.push([value,value.unique_id,value.Allocation,gantttask.dyn_belt,true]); // new object, new id, new allocation. old allocation
            }
        } else{
            console.log("Found flight that doesn't exist in init plan ",value);
            var starttime = ultimateDateFormatter(value.STA,-2)
            var endtime = ultimateDateFormatter(value.STA)
            if((start_time>starttime)&&(endtime>starttime)){
                updateList.push([value,value.unique_id,value.Allocation,0,false]); // new object, new id, new allocation. old allocation==0, old flight?
            }
        }
    });
    currentSimulationTime=ultimateDateFormatter(start_time);
}

/*
update gantt interface
*/
var updateGantt = function updateGantt(updateConfirmList){
    updateCSVList=[];
    var success=true;
    var failedtask=null;
    var temp_initBigARMAllocation= jQuery.extend(true, {}, initBigARMAllocation);
    // delete the original from the temp_initbigarmallocation
    if(updateConfirmList==[]){
        return updateCSVList;
    }
    updateConfirmList.forEach(element => {
        if(element[4]==true){
            var temp_gantttask= jQuery.extend(true, {}, gantt.getTask(element[0]));
            var original_parent=temp_gantttask.parent-1;
            temp_initBigARMAllocation[original_parent] = temp_initBigARMAllocation[original_parent].filter(function( obj ) {
                return obj.id !== element[0];
            });
        } else{
            
        }

    });
    // add it back
    updateConfirmList.forEach(element => {
        if(element[4]==true){ // existing flight
            var temp_gantttask= jQuery.extend(true, {}, gantt.getTask(element[0]));
            var STA = ultimateDateFormatter(element[3].STA);
            temp_gantttask.start_date=STA;
            temp_gantttask.STA=STA;
            var foundParent=findParentPre(element[1]-1,temp_gantttask,temp_initBigARMAllocation);
            if(foundParent>-1){
                temp_initBigARMAllocation[foundParent-1].push(temp_gantttask);
            }else{
                success=false;
                failedtask=element;
            }
        } else{ // new flight
            var temp2=element[0];
            var Flight_no2=element[3].Flight_no;
            var STA2 = ultimateDateFormatter(element[3].STA);
            var temp_gantttask2 = {STA:STA2, duration:1}; 
            var Flight_time2=STA2.getFullYear()  + "-" + ("0"+(STA2.getMonth()+1)).slice(-2) +"-"+("0" + STA2.getDate()).slice(-2) + " " + ("0" + STA2.getHours()).slice(-2) + ":" + ("0" + STA2.getMinutes()).slice(-2)+":00";
            var foundParent2=findParentPre(element[1]-1,temp_gantttask2,temp_initBigARMAllocation);

            if(foundParent2>-1){
                temp_initBigARMAllocation[foundParent2-1].push(temp_gantttask2);
            }else{
                success=false;
                failedtask=element;
            }
        }
    });

    if(success){
        manualConfirmUpdate(updateConfirmList);

    } else{
        alert('2Flight2 '+failedtask[0]+' on carousel '+(parseInt(failedtask[2],10)+1)+" is moved to carousel "+(failedtask[1]+1)+", which is full\nPlease change to different carousel");
        success=false;
    }
}

var updateGanttPartTwo = function updateGanttPartTwo(){

    updateConfirmList.forEach(element => {
        if(element[4]==true){
            var temp_gantttask= jQuery.extend(true, {}, gantt.getTask(element[0]));
            var original_parent=temp_gantttask.parent-1;
            initBigARMAllocation[original_parent] = initBigARMAllocation[original_parent].filter(function( obj ) {
                return obj.id !== element[0];
            });
        } else{

        }
    });

    updateConfirmList.forEach(element => {
        var temp=element[0];
        var Flight_no=element[3].Flight_no;
        var STA = ultimateDateFormatter(element[3].STA);
        var Flight_time=STA.getFullYear()  + "-" + ("0"+(STA.getMonth()+1)).slice(-2) +"-"+("0" + STA.getDate()).slice(-2) + " " + ("0" + STA.getHours()).slice(-2) + ":" + ("0" + STA.getMinutes()).slice(-2)+":00";
        var datatemp = data.find(x => x.unique_id === element[0]);
        datatemp.Allocation=element[1];
        datatemp.changed=true;
        var update = {'Flight_no':Flight_no,'Unique_id':temp, 'Allocation': element[1],'Flight_time': Flight_time};
        updateCSVList.push(update);

    });

    for(var i=0;i<60;i++){
        initBigARMAllocation[i]=[];
    }
    mappedDataArr = [];
    minuteLoadBigArmInit = [];
    $.each( data, function( key, value ) {
        if(value.Allocation>0){
            var newTask = propertyMap(value,-1);
            if(newTask!=-1){ // ignore the > 5 ones            
                mappedDataArr.push(newTask);
            } else{
                var newCarousel = moveToMin(ultimateDateFormatter(value.STA));
                value.Allocation = newCarousel+1;
                var newTask2 = propertyMap(value,-1);
                if(newTask2!=-1){
                    mappedDataArr.push(newTask2);
                } else{
                }
            }
        }

    });

    gantt.clearAll();
    if (date >= new Date("2019-06-20")) gantt.parse(bj2);
    else gantt.parse(bj);
    gantt.parse({"data":  mappedDataArr});
    gantt.render();


}

var manualConfirmUpdate = function manualConfirmUpdate(list){
    // (parseInt(element[2],10)+1 old
    // (element[1]+1) new
    var str="";
    var i = 1;
    list.forEach(element => {
        var gantt_id=element[0];
        var ogtime;
        var timegap;
        var msg;
        var newtime=ultimateDateFormatter(element[3].STA);
        var newtimeStr = newtime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        if(element[4]==true){
            ogtime=ultimateDateFormatter(gantt.getTask(gantt_id).STA);
            timegap= (newtime-ogtime);
            timegap=Math.floor(timegap / 60000);
            msg=(timegap>0)?("<span style='color:red;'>"+timegap+" minutes late</span>"):(timegap<0)?("<span style='color:green;'>"+Math.abs(timegap)+" minutes early</span>"):"";
        } else{
            msg="<span style='color:green;'> (new flight)</span>"
        }    
        var original_carousel=parseInt(element[2],10);//original carousel
        var final_carousel=element[1];
        var new_carousel=parseInt(element[3].Allocation,10);
        var load=element[3].Load;
        str=str+"<tr><td>"+i+". "+element[3].Flight_no+"</td><td>"+newtimeStr+"<br>"+msg+"</td><td>"+load+"</td><td>"+ultimateCarouselFormatter(original_carousel)+"</td><td>"+ultimateCarouselFormatter(new_carousel)+"</td><td>"+ultimateCarouselFormatter(final_carousel)+"</td>";
        i++;
    });
    document.getElementById("updateModalTable_confirm").innerHTML = str; 
    realtimemodal_confirm.style.display = "block";
}



var modalView= function modalView(){

    var classname="realtime_select";
    var selectStr1='<div class="flexcontainer"><div id="select-carousel"><select temp_belt=0 ganttid="';
    var selectStr1_3='"class="';
    var selectStr1_4='"original-carousel="';
    var selectStr1_5='" id="';
    var selectStr1_6='" latest-time="';
    var selectStr1_7='" realtime-carousel="';
    var selectStr1_8='" load="';

    var date2 = new Date(date);
    var selectStr2;
    if (date2 <= new Date("2019-06-19")) {
      selectStr2='" onchange="changeInitplan_rt(this)"><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option><option>11</option><option>12</option><option>13</option></select>';
    } else {
      selectStr2='" onchange="changeInitplan_rt(this)"><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option><option>12</option><option>13</option><option>14</option><option>15</option><option>16</option><option>17</option></select>';
    }
    var selectStr2_1='<span class="red-star" style="color:red;" id="';
    var selectStr2_2='">*</span> &#09;<input type="checkbox" class="checkbox_realtime" onchange="changeCheckBox(this,1)" id="';
    var selectStr2_3='"> <input type="checkbox" class="checkbox_realtime2" onchange="changeCheckBox(this,2)" id="';
    var selectStr2_4='"></div></div>';

    temp_minuteLoadBigArmInit = jQuery.extend(true, {}, minuteLoadBigArmInit);
    var str="";
    var i = 1;
    if(updateList.length==0){
        document.getElementById('simulation_msg').innerHTML="Nothing to change in the next 2 hours";
        document.getElementById('table_realtime').style.display="none";
        document.getElementById("current-time").innerHTML = start_time; 
    } else{
        document.getElementById('simulation_msg').innerHTML="";
        document.getElementById('table_realtime').style.display="block";
        updateList.forEach(element => {
            var id="mySelect_rt"+i.toString();
            var ogtime=ultimateDateFormatter(element[0].STA);
            var temp_date=ultimateDateFormatter(element[0].STA);
            var gantt_id = element[1];
            var dateAttr = temp_date.getFullYear()+ "-" +('0' + (temp_date.getMonth()+1)).slice(-2) +"-" +('0' + temp_date.getDate()).slice(-2);
            var timeAttr = temp_date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            var realtime_carousel=element[2];
            var original_carousel=element[3];//original carousel
            var load=element[0].Load;
            var style="";
            if(parseInt(element[3],10) == element[0].Allocation){
                style=" style='display:none;'";
            } else if(!element[4]){
                // new flight
                style=" style='background-color: #99ccff;'";
            }
            str=str+"<tr"+style+"><td>"+i+". "+element[0].Flight_no+"</td><td>"+dateAttr+"</td><td>"+timeAttr+"</td><td>"+timeAttr+"</td><td>"+element[0].Load+"</td><td>"+ultimateCarouselFormatter(parseInt(element[3],10))+"</td><td>"+ultimateCarouselFormatter(parseInt(element[2],10))+"</td><td>"+selectStr1+gantt_id+selectStr1_3+classname+selectStr1_4+original_carousel+selectStr1_5+id+selectStr1_6+ogtime+selectStr1_7+realtime_carousel+selectStr1_8+load+selectStr2+selectStr2_1+id+"star"+selectStr2_2+id+"check"+selectStr2_3+id+"checc"+selectStr2_4+"</td>";
            i++;
        });
        document.getElementById("updateModalTable2").innerHTML = str; 
        document.getElementById("current-time").innerHTML = start_time; 
        var j=1;
        updateList.forEach(element => {
            var id="mySelect_rt"+j.toString();
            document.getElementById(id).selectedIndex=element[0].Allocation-1;
            j++;
            var temp_date= ultimateDateFormatter(element[0].STA);
            document.getElementById(id).setAttribute("latest-time",temp_date);
            document.getElementById(id).setAttribute("temp_belt",element[2]); // new allocation 1-12
            var minutes=temp_date.getMinutes()+temp_date.getHours()*60-180;
            var load = parseInt(element[0].Load,10);
            // if(parseInt(element[3],10)==0){
            //     console.log("load ",load);
            // }
            // 把tempload的时间和传送带都换了
            // 把originalload的换了：同一个传送带，不同的时间
            // updatelist 里需要有carousel相同时间不同的flight
            if(element[4]){
                var temp_date_old= ultimateDateFormatter(gantt.getTask(element[0].unique_id).start_date);
                var minutes_old=temp_date_old.getMinutes()+temp_date_old.getHours()*60-180;

                for(var k=minutes_old;k<minutes_old+60;k++){
                    if(temp_minuteLoadBigArmInit[k]==undefined){
                        temp_minuteLoadBigArmInit[k]=[0,0,0,0,0,0,0,0,0,0,0,0]
                    }
                    temp_minuteLoadBigArmInit[k][parseInt(element[3],10)-1]-=load;//old
    
                    if(minuteLoadBigArmInit[k]==undefined){
                        minuteLoadBigArmInit[k]=[0,0,0,0,0,0,0,0,0,0,0,0]
                    }
                    minuteLoadBigArmInit[k][parseInt(element[3],10)-1]-=load;//old
                }
            }

            for(var l=minutes;l<minutes+60;l++){
                if(temp_minuteLoadBigArmInit[l]==undefined){
                    temp_minuteLoadBigArmInit[l]=[0,0,0,0,0,0,0,0,0,0,0,0] 
                }
                temp_minuteLoadBigArmInit[l][element[0].Allocation-1]+=load;//new

                if(minuteLoadBigArmInit[l]==undefined){
                    minuteLoadBigArmInit[l]=[0,0,0,0,0,0,0,0,0,0,0,0] 
                }
                minuteLoadBigArmInit[l][parseInt(element[3],10)-1]+=load;//new
            }


        });
    }
    
    if(simulationMode==0){//realtime mode
        document.getElementById("end_realtime").innerHTML="End Recommendation";
    } else{
        document.getElementById("end_realtime").innerHTML="End Simulation";
    }
    document.getElementById("update_sentence").innerHTML="Updates ("+updateList.length+" Flights)";
    realtimemodal.style.display = "block";

    drawLineChart('myLineChart_min_realtime',3);//myLineChart_min_old
    calculateALLSTD(3,0);  // 0表示第一次
}

var setColorDarker = function setColorDarker(load) {
    if (load<80&&load>0){return"#086010 !important";} // green
    else if (load>=80&&load<160){return"#82761f !important";} // yellow
    else if (load>=160&&load<240){return"#477d8e !important";} // blue
    else if (load>=240&&load<320){return"#915c1f !important";} //orange
    else if (load>=320){return"#661515 !important";} //red
};

/*
show temporary change on recommendation window
*/
var changeInitplan_rt = function changeInitplan_rt(obj){
    var latest_time=new Date(obj.getAttribute('latest-time'));
    var minutes=latest_time.getMinutes()+latest_time.getHours()*60-180;
    var load = parseInt(obj.getAttribute('load'),10);
    var original_carousel=(parseInt(obj.getAttribute('temp_belt'),10)==  0)?parseInt(obj.getAttribute('original-carousel'),10)-1:parseInt(obj.getAttribute('temp_belt'),10)-1;
    if(parseInt(obj.getAttribute('original-carousel'),10)==0){
        //console.log("新！的！飞！机！：");
    }
    // change star color if different than original carousel
    if(parseInt(obj.getAttribute('original-carousel'),10)-1!=obj.selectedIndex){
        document.getElementById(obj.id+"star").style.color="red";
    }else{
        document.getElementById(obj.id+"star").style.color="white";
    }
    obj.setAttribute("temp_belt", obj.selectedIndex+1);
    
    for(var i=minutes;i<minutes+60;i++){
        temp_minuteLoadBigArmInit[i][original_carousel]-=load;
        temp_minuteLoadBigArmInit[i][obj.selectedIndex]+=load;
    }
    // update linechart
    calculateALLSTD(3,1);  // 1表示要做对比了
}

$('#confirm_confirm_update').click(()=>{
    realtimemodal_confirm.style.display = "none";
    updateGanttPartTwo();
    if(simulationMode==1){
        sendUpdates(updateCSVList);
    } else if(simulationMode==0){
        sendUpdatesNotSimulation(updateCSVList);
    }
    minuteLoadBigArmInit = jQuery.extend(true, {}, temp_minuteLoadBigArmInit);
    calculateALLSTD(1,0);
    realtimemodal.style.display = "none";
});

$('#cancel_update').click(()=>{
    realtimemodal_confirm.style.display = "none";
    
});

$('#close_simulation_input').click(()=>{
    simulationMode=-1;
    realtimeLoopNo=0;
    realtimemodal_input.style.display = "none";
    
});

$('#end_realtime').click(()=>{
    simulationMode=-1;
    realtimeLoopNo=0;
    updateList=[];
    document.getElementById("simulation").disabled = false;
    document.getElementById("realtime").disabled = false;
    realtimemodal.style.display="none";
    end_realtime()
});

var checkModalView = function checkModalView(checkCount){
    console.log("check");
    if((currentSimulationTime==undefined)||(currentSimulationTime.getTime()!=start_time.getTime())){
        // if(checkCount<=40){
        if(checkCountBoolean){
            setTimeout(function(){
                checkCount=checkCount+1;
                checkModalView(checkCount);
            }, 1000);
        }

    } else{
        modalView();
    }
}

$('#confirm_update').click(()=>{
    var i=0;
    if(!checkIfClearSearch_realtime()){
        alert("Please clear your search first");
    } else{
        updateConfirmList=[];
        if(updateList.length!=0){
            document.querySelectorAll('.realtime_select').forEach(function(element) {
                var temp = updateList.find(x => x[1] === element.getAttribute('ganttid'));
                updateConfirmList.push([element.getAttribute('ganttid'),element.selectedIndex+1,element.getAttribute('original-carousel'),temp[0],temp[4]]);
            });
            updateGantt(updateConfirmList);
        } else { // nothing to update, close window and send updates
            if(simulationMode==1){
                sendUpdates([]);
            } else if(simulationMode==0){
                sendUpdatesNotSimulation([]);
            }
            minuteLoadBigArmInit = jQuery.extend(true, {}, temp_minuteLoadBigArmInit);
            calculateALLSTD(1,0);
            realtimemodal.style.display = "none";
        }   
    }
});

var hideWindow = function hideWindow(obj){
    realtimemodal.getElementsByClassName("modal-content")[0].style.opacity=0.1;
}

var showWindow = function showWindow(){
    realtimemodal.getElementsByClassName("modal-content")[0].style.opacity=1;
}

/*
let load array of certain time (minute unit)
*/
var getMinuteLoad = function getMinuteLoad(){
    var zero = date;
    var minutesSinceBeginning=0;
    if (start_time>=zero) {
        minutesSinceBeginning = (start_time-zero)/(1000*60);
    }
    // var minimum = Math.min(...minuteLoadBigArmInit[minutesSinceBeginning]);
    if(minuteLoadBigArmInit[minutesSinceBeginning]==undefined){
        return [0,0,0,0,0,0,0,0,0,0,0,0];
    } else{
        return minuteLoadBigArmInit[minutesSinceBeginning];
    }
};

$('#search_btn_realtime').click(()=>{
    var input_flight, filter_flight, table, tr, td_flight, i, txtValue;
    var input_time1, input_time2;
    input_flight = document.getElementById("search_realtime");
    input_time1 = document.getElementById("searchtime_from_realtime");
    input_time2 = document.getElementById("searchtime_to_realtime");

    filter_flight = input_flight.value.toUpperCase();
    filter_flight = filter_flight.replace(/\s+/g,'');
    filter_from = new Date(date_str+" "+input_time1.value);
    filter_to = new Date(date_str+" "+input_time2.value);

    table = document.getElementById("table_realtime");
    table.setAttribute("filtered",1);
    tr = table.getElementsByTagName("tr");

    for (i = 0; i < tr.length; i++) {
        // filter flight id
        td_flight = tr[i].getElementsByTagName("td")[0];
        td_time = tr[i].getElementsByTagName("td")[1];

        if (td_flight && td_time) {
            txtValue = td_flight.textContent || td_flight.innerText;
            txtValue = txtValue.replace(/\s+/g,'');
            txtValue_flight = td_time.textContent || td_time.innerText;
            flight_time=new Date(txtValue_flight);

            if(txtValue.toUpperCase().indexOf(filter_flight) > -1 && flight_time>=filter_from && flight_time<=filter_to){
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }    
    }
});

$('#clearsearch_btn_realtime').click(()=>{
    var input_flight, filter_flight, table, tr, td_flight, i, txtValue;
    var input_time1, input_time2;
    input_flight = document.getElementById("search_realtime");
    input_time1 = document.getElementById("searchtime_from_realtime");
    input_time2 = document.getElementById("searchtime_to_realtime");

    input_flight.value="";
    input_time1.value="00:00";
    input_time2.value="23:59";

    filter_flight = input_flight.value.toUpperCase();
    filter_from = new Date(date_str+" "+input_time1.value);
    filter_to = new Date(date_str+" "+input_time2.value);

    table = document.getElementById("table_realtime");
    table.setAttribute("filtered",0);
    tr = table.getElementsByTagName("tr");

    for (i = 0; i < tr.length; i++) {
        // filter flight id
        td_flight = tr[i].getElementsByTagName("td")[0];
        td_time = tr[i].getElementsByTagName("td")[1];

        if (td_flight && td_time) {
            txtValue = td_flight.textContent || td_flight.innerText;
            txtValue_flight = td_time.textContent || td_time.innerText;
            flight_time=ultimateDateFormatter(txtValue_flight);
            if(txtValue.toUpperCase().indexOf(filter_flight) > -1 && flight_time>=filter_from && flight_time<=filter_to){
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }    
    }
    
});

var checkIfClearSearch_realtime = function checkIfClearSearch_realtime(){
    var table = document.getElementById("table_realtime");
    if(parseInt(table.getAttribute("filtered"),10)){
        return false;
    } else return true;

}