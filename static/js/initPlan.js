var initplanmodal = document.getElementById('myModal_initplan');

function getInitplanData(){
    // get new datas and compare
    $.each( data, function( key, value ) {
        // if found in update list, change first into new value
        updateList.push([value,value.Flight_no,value.Allocation,value.Allocation]); // dynamic allocation, old allocation
    });
    modalView_initplan(updateList);
}


var updateGantt_initplan = function updateGantt_initplan(list) { //unique_id, new allocation, old [1,12]
    var success = true;
    var failedtask = null;
    var temp_initBigARMAllocation = jQuery.extend(true, {}, initBigARMAllocation);
    list.forEach(element => {
        var unique_id = element[1];
        console.log("unique ",unique_id);
        var foundParent = findParentPre(element[2] - 1, gantt.getTask(unique_id), temp_initBigARMAllocation);
        if (foundParent > -1) {
            temp_initBigARMAllocation[foundParent - 1].push(gantt.getTask(unique_id));
        } else {
            success = false;
            failedtask = element;
        }
    });
    if (success) {
        list.forEach(element => {
            var unique_id = element[1];
            try{
                var foundParent = findParentPre(element[2] - 1, gantt.getTask(unique_id),initBigARMAllocation);
                if (foundParent > -1) {
                    var parent = gantt.getTask(unique_id).parent - 1;
                    // update data
                    var temp = data.find(x => x.unique_id === element[1]);
                    temp.Allocation = element[2];
                    // update initBigARMAllocation
                    var index = initBigARMAllocation[parent].findIndex(x => x.id === element[1]);
                    if (index > -1) {
                        initBigARMAllocation[parent].splice(index, 1);
                    }
                    initBigARMAllocation[foundParent - 1].push(gantt.getTask(unique_id));
                    // update gantt
                    gantt.getTask(unique_id).parent = foundParent;// update bigarminit, element[2] is new data
                    gantt.getTask(unique_id).dyn_belt =  ultimateCarouselFormatter(element[2]);
                    gantt.getTask(unique_id).changed=true;
                    gantt.updateTask(unique_id); 
                } else {
                    alert('Flight ' + element[1] + ' on carousel ' + ultimateCarouselFormatter(parseInt(element[3], 10)) + " is moved to carousel " + ultimateCarouselFormatter(element[2]) + ", which is full\nPlease change to different carousel");
                }
            } catch(err){
                console.log(err);
            }
        });
    } else {
		alert('Flight ' + failedtask[0] + ' on carousel ' + ultimateCarouselFormatter(parseInt(failedtask[2], 10)) + " is moved to carousel " + ultimateCarouselFormatter(failedtask[1]) + ", which is full\nPlease change to different carousel");
        success = false;
    }
    return success;

}


var changeInitplan = function changeInitplan(obj){//temp change
    var gantt_id=obj.getAttribute('ganttid');
    var flight_task=gantt.getTask(gantt_id);
    var STA = ultimateDateFormatter(flight_task.STA);
    var minutesSinceBeginning = (STA-date)/(1000*60)-180;
    var load = flight_task.load;
    var original_carousel=(obj.getAttribute('temp_belt')==0)?obj.getAttribute('original-carousel')-1:obj.getAttribute('temp_belt')-1;
    if(obj.getAttribute('original-carousel')-1!=obj.selectedIndex){
        document.getElementById(obj.id+"star").style.color="red";
    }else{
        document.getElementById(obj.id+"star").style.color="white";
    }

    obj.setAttribute("temp_belt", obj.selectedIndex+1);
    
    for(var i=minutesSinceBeginning;i<minutesSinceBeginning+60;i++){
        temp_minuteLoadBigArmInit[i][original_carousel]-=load;
        temp_minuteLoadBigArmInit[i][obj.selectedIndex]+=load;
    }
    calculateALLSTD(2);

}

var changeCheckBox = function changeCheckBox(obj,type){
    if (obj.checked){
        var id = obj.id;
        id=id.substring(0, obj.id.length - 5);
        var select = document.getElementById(id);
        if(type==0){
            select.selectedIndex=parseInt(select.getAttribute('original-carousel'),10)-1;
            changeInitplan(select);
            document.getElementById(id+"star").style.color="white";
        } else if(type==1){
            select.selectedIndex=parseInt(select.getAttribute('original-carousel'),10)-1;
            changeInitplan_rt(select);
            document.getElementById(id+"star").style.color="white";
        } else if(type==2){
            select.selectedIndex=parseInt(select.getAttribute('realtime-carousel'),10)-1;
            changeInitplan_rt(select);
        }
        if(obj.id.substring(obj.id.length - 5, obj.id.length)=="check"){
            document.getElementById(id+"checc").checked=false;
        } else if(obj.id.substring(obj.id.length - 5, obj.id.length)=="checc"){
            document.getElementById(id+"check").checked=false;
        }
    }
}

var changeAllCheckBox = function changeAllCheckBox(obj,type) {
    var checkboxclass;
    if(type=="initplan") checkboxclass=".checkbox_initplan";
    else if (type=="realtime1") checkboxclass=".checkbox_realtime";
    else if (type=="realtime2") checkboxclass=".checkbox_realtime2";

    if (obj.checked){
        document.querySelectorAll(checkboxclass).forEach(v=>{
            v.checked=true;
            var id = v.id;
            id=id.substring(0, v.id.length - 5);
            var select = document.getElementById(id);
            if(type=="initplan"){
                select.selectedIndex=parseInt(select.getAttribute('original-carousel'),10)-1;
                changeInitplan(select);
                document.getElementById(id+"star").style.color="white";
            } else if(type=="realtime1"){
                select.selectedIndex=parseInt(select.getAttribute('original-carousel'),10)-1;
                changeInitplan_rt(select);
                document.getElementById(id+"star").style.color="white";
            } else if(type=="realtime2"){
                select.selectedIndex=parseInt(select.getAttribute('realtime-carousel'),10)-1;
                changeInitplan_rt(select);
            }
        });
        if(obj.id=="checkAll1"){
            document.getElementById("checkAll2").checked=false;
            document.querySelectorAll(".checkbox_realtime2").forEach(v=>{
                v.checked=false;
            });
        } else if(obj.id=="checkAll2"){
            document.getElementById("checkAll1").checked=false;
            document.querySelectorAll(".checkbox_realtime").forEach(v=>{
                v.checked=false;
            });
        }

    } else{
        document.querySelectorAll(checkboxclass).forEach(v=>{
            v.checked=false;
        });
    }
};

$('#search_btn').click(()=>{
    var input_flight, filter_flight, table, tr, td_flight, i, txtValue;
    var input_time1, input_time2;
    input_flight = document.getElementById("search_initplan");
    input_time1 = document.getElementById("searchtime_from_initplan");
    input_time2 = document.getElementById("searchtime_to_initplan");

    filter_flight = input_flight.value.toUpperCase();
    filter_from = new Date(date_str+" "+input_time1.value);
    filter_to = new Date(date_str+" "+input_time2.value);

    table = document.getElementById("table_initplan");
    table.setAttribute("filtered",1);
    tr = table.getElementsByTagName("tr");

    for (i = 0; i < tr.length; i++) {
        // filter flight id
        td_flight = tr[i].getElementsByTagName("td")[0];
        td_time = tr[i].getElementsByTagName("td")[1];

        if (td_flight && td_time) {
            txtValue = td_flight.textContent || td_flight.innerText;
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

$('#clearsearch_btn').click(()=>{
    var input_flight, filter_flight, table, tr, td_flight, i, txtValue;
    var input_time1, input_time2;
    input_flight = document.getElementById("search_initplan");
    input_time1 = document.getElementById("searchtime_from_initplan");
    input_time2 = document.getElementById("searchtime_to_initplan");

    input_flight.value="";
    input_time1.value="00:00";
    input_time2.value="23:59";

    filter_flight = input_flight.value.toUpperCase();
    filter_flight = filter_flight.replace(/\s+/g,'');
    filter_from = new Date(date_str+" "+input_time1.value);
    filter_to = new Date(date_str+" "+input_time2.value);

    table = document.getElementById("table_initplan");
    table.setAttribute("filtered",0);
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

var modalView_initplan= function modalView_initplan(list){
    var classname="initplan_select";
    var selectStr1='<div class="flexcontainer"><div id="select-carousel"><select temp_belt=0 ganttid="';
    var selectStr1_3='"class="';
    var selectStr1_4='"original-carousel="';
    var selectStr1_5='" id="';
    var selectStr1_6 = '" flightid="';
    var date2 = new Date(date);
    if (date2 <= new Date("2019-06-19")) {
      var selectStr2='" onchange="changeInitplan(this)"><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option><option>11</option><option>12</option><option>13</option></select>';
    } else {
      var selectStr2='" onchange="changeInitplan(this)"><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option><option>12</option><option>13</option><option>14</option><option>15</option><option>16</option><option>17</option></select>';
    }

    var selectStr2_1='<span class="red-star" id="';
    var selectStr2_2='">*</span>  <input type="checkbox" class="checkbox_initplan" onchange="changeCheckBox(this,0)" id="';
    var selectStr2_3='"></div></div>';

    temp_minuteLoadBigArmInit = jQuery.extend(true, {}, minuteLoadBigArmInit);
    var str="";
    var i = 1;
    list.forEach(element => {
        var gantt_id=element[0].unique_id;
        var flight_id = element[0].Flight_no;
        var id="mySelect"+i.toString();
        var original_carousel=element[3];//original carousel
        str=str+"<tr><td>"+element[0].Flight_no+"</td><td>"+element[0].STA+"</td><td>"+element[0].Load+"</td><td>"+ultimateCarouselFormatter(parseInt(element[2], 10))+"</td><td>"+selectStr1+gantt_id+selectStr1_3+classname+selectStr1_4+original_carousel+selectStr1_5+id+selectStr1_6+flight_id+selectStr2+selectStr2_1+id+"star"+selectStr2_2+id+"check"+selectStr2_3+"</td>";
        i++;
    });
    document.getElementById("updateModalTable_initplan").innerHTML = str;
    var j=1;
    list.forEach(element => {
        var id="mySelect"+j.toString();
        document.getElementById(id).selectedIndex=element[0].Allocation-1;
        j++;
    });
    initplanmodal.style.display = "block";

    drawLineChart('myLineChart_min_old',2);//myLineChart_min_old
    calculateALLSTD(2);
}

$('#confirm_initplan').click(()=>{
    var i=0;
    if(!checkIfClearSearch()){
        alert("Please clear your search first");
    } else{
        var list=[];
        document.querySelectorAll('.initplan_select').forEach(function(element) {
            if(element.getAttribute('original-carousel')!=element.selectedIndex+1){
                list.push([element.getAttribute('flightid'), element.getAttribute('ganttid'),element.selectedIndex+1,element.getAttribute('original-carousel')]);
            }
        }); 
        if(updateGantt_initplan(list)){
            // success, ajax back ->
            sendInitPlanUpdates(list)
            minuteLoadBigArmInit = jQuery.extend(true, {}, temp_minuteLoadBigArmInit);
            calculateALLSTD(1);
            updateList=[];
            initplanmodal.style.display = "none";
            temp_minuteLoadBigArmInit=[]
        } else{
        }
    }

});


$('#close_initplan').click(()=>{
    initplanmodal.style.display='none';
    temp_minuteLoadBigArmInit = jQuery.extend(true, {}, minuteLoadBigArmInit);
    calculateALLSTD(2);
  });

$('#open_init_plan').click(()=>{
    getInitplanData();
  });

var hideWindow_init = function hideWindow(obj){
    initplanmodal.getElementsByClassName("modal-content-initplan")[0].style.opacity=0.1;
}

var showWindow_init = function showWindow(){
    initplanmodal.getElementsByClassName("modal-content-initplan")[0].style.opacity=1;
}

var checkIfClearSearch = function checkIfClearSearch(){
    var table = document.getElementById("table_initplan");
    if(parseInt(table.getAttribute("filtered"),10)){
        return false;
    } else return true;

}

var sendInitPlanUpdates = function sendInitPlanUpdates(list){
    $.ajax({
        method: 'POST',
        dataType: 'json',
        url: '/update_initplan',  
        data: {
            date: date_str,
            updateList:JSON.stringify(list),
            initialize: false
        },
        success: function (response) {
            if (!response.Error) {
                console.log("init update response",response);
            } else {
                alert(response.Msg+"init update failed 1");
            }
        },
        error: function (error) {
            alert(error.message+"init update failed 2");
        }
    })
}