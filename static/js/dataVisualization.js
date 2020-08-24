var data={};
var cvs_data="";
var updateList=[];
var updateConfirmList=[];
var updateCSVList=[];
var date= new Date();
date.setHours(0,0,0,0);
var date_str;
var mappedDataArr = [];
var minuteLoadBigArmInit = [];//around 1440 entrys 60minutes * 24 hours
var temp_minuteLoadBigArmInit=[];
var stdBigArmInit = [];//for line chart showing std
var lineChart;
var lineChart_min_old;//2
var lineChart_min_realtime;//3
var barChart;
// var modalBarChart;
var currentMarker;
var initBigARMAllocation = new Array(60);
//var logger = log4javascript.getDefaultLogger();
// var log4js = require('log4js');
// var logger = log4js.getDefaultLogger()

for(var i=0;i<60;i++){
    initBigARMAllocation[i]=[];
}
var interval;
var realtime_interval;
var currentFlight=0; //current flight
var point = 0;
var modal = document.getElementById('myModal');
var disablecarousel = document.getElementById('myModal_disablecarousel')
var upload = document.getElementById('myModal_upload')
var viewmaintenance = document.getElementById('myModal_viewmaintenance')
var changeinitPlan = document.getElementById('myModal_initplan')
var showModalBoolean = false;

// var auth;

initBigARMGantt();
drawBarChart();
drawLineChart('myLineChart',1);//linechart

$('#get_initial_bigarm_plan').click(()=>{	
    interval = setInterval(function(){ 
        newFlight(); 
    }, 600); //40
		// if(auth != 0){
		// alert ("Super User");
	// }else{
		// alert ("Common guy");
    if(data.length!=undefined){		
        document.getElementById("get_initial_bigarm_plan").disabled = true;
    }else{
        alert("Please select a date.");
    }	
});

$('#stop_auto').click(()=>{
    if(interval!=undefined && data.length!=undefined){
        clearInterval(interval);
        //document.getElementById("get_initial_bigarm_plan").disabled = false;
    }else{
        alert("Please select a date.");
    }
});

$('#get_initial_bigarm_plan_next').click(()=>{
    newFlight();
    if(data.length!=undefined){
        //document.getElementById("get_initial_bigarm_plan").disabled = false;
    }else{
        alert("Please select a date.");
    }
});
$('#show_all_flights').click(()=>{
    if(data.length!=undefined){
      document.getElementById("show_all_flights").disabled = true;
      document.querySelector("#displayButton").disabled = true; //disable gradual display button
    } else{
        alert("Please select a date.");
    }
    showALL();
    // logger.info('Show All Button Pressed.');
    calculateALLSTD(1,0);
    document.getElementById("simulation").disabled = false;
    
});

$('#change_carousel_status').click(()=>{
    if(data.length!=undefined){
        changeinitPlan.style.display = "block";
        getInitplanData();
        console.log("Btn pressed");
    } else{
        alert("Please select a date.");
    }
});

$('#disable_carousel').click(()=>{
    disablecarousel.style.display = "block";
});

$('#upload').click(()=>{
    var date_str = localStorage.getItem('my_form_date');	
    if (date_str == null) {
        console.log("Please select date first");
        alert('Please select the date and Press "BigARM Plan" button first');
    }else {
        upload.style.display = "block";
    }
    console.log(date_str);
});

$('#myModal_viewmaintenance').load(function() {
    console.log("View outstanding schedule!");
  });

$('#close_disable_carousel').click(()=>{
    disablecarousel.style.display="none";
});

$('#close_upload').click(()=>{
    upload.style.display="none";
});

$('#userlogin').click(()=>{
    console.log("Login Button Clicked!!")
});

$('#confirm_disable_carousel').click(()=>{
    disablecarousel.style.display="none";
    // if(data.length!=undefined){  //Set need enter date first
    //     disablecarousel.style.display="none";
    // } else{
    //     //    alert("Please select date first.");
    //     //    disablecarousel.style.display="none";
    //     //    document.getElementById("disable_carousel").disabled = true;
    // }
});

$('#addDisableField').click(()=>{
   console.log("Add Btn Clicked!!");
   var container = $('<tr></tr>');
   var selection = '<td><select type="text" id="selected_carousel[]" name="selected_carousel[]">' + '<option value="0">5</option><option value="1">6</option>' +
            '<option value="2">7</option><option value="3">8</option><option value="4">9</option><option value="5">10</option>'+
            '<option value="6">12</option><option value="7">13</option><option value="8">14</option><option value="9">15</option>' + '<option value="10">16</option><option value="11">17</option></select></td>';
   var StartTime = '<td><input type="datetime-local" name="disabletime_S[]" id="disabletime_S[]" max="31-12-9999" required></td>';
   var EndTime = '<td><input type="datetime-local" name="disabletime_E[]" id="disabletime_E[]" max="31-12-9999" required></td>';
   var Removebtn = $('<td><button id="removedisable" type="button">Remove</button></td>');
   var DateCol = $('<td></td>');
   var Current = moment(); 
   DateCol.html(Current.format());
   // var CurrentT = '<td><p id="addDisableField"></p></td>';
   container.append(selection,StartTime,EndTime,Removebtn,DateCol);
   $('#removedisable',container).click(()=>{
    container.remove();
    console.log("Remove Button Clicked!!");
    });

    $("#select_disable_carousel").append(container);
});

var newFlight = function newFlight(){
    if (currentFlight<data.length) {
        if(showModalBoolean==true){//直接弹出窗口   //parseFloat(data[currentFlight].Load)>=160&& 
            showModal(data[currentFlight]);
            clearInterval(interval); 
        } else{//直接找carousel
            var newTask = propertyMap(data[currentFlight],-1);
            if(newTask==-1){//carousel满了，问用户放哪里
                // var message = "The automatic generated carousel for this flight is full, please choose a different carousel";
                // showModal(data[currentFlight],message);
                // clearInterval(interval); 
                var newCarousel = moveToMin(new Date(data[currentFlight].STA));
		        data[currentFlight].Allocation = newCarousel+1;
                var newTask2 = propertyMap(data[currentFlight],-1);
                if(newTask2!=-1){
                    addFlight(newTask2);
                } else{
                    // use loop here?
                    currentFlight++;// comment this 
                }
            } else{//直接放load
                addFlight(newTask);
            }
        }
    } else {
        if(interval!=undefined){
            clearInterval(interval);
        }
    }
};

var toggleModal = function toggleModal(toggle){
    toggle.checked? showModalBoolean=false:showModalBoolean=false;
}

var showModal = function  showModal(flightInfo,message=""){ //Alan
    var carousel = ultimateCarouselFormatter(parseInt(flightInfo.Allocation,10));
    document.getElementById("modal-body-information").innerHTML = "<p>Flight ID: "+flightInfo.Flight_no+"</p><p>Start Time: "+flightInfo.STA+"</p><p>Load: "+parseFloat(flightInfo.Load)+"</p><p>Carousel: "+carousel+"</p>";
    document.getElementById("mySelect").selectedIndex = flightInfo.Allocation-1;
    document.getElementById("modal-message").innerHTML = message;
    modal.style.display = "block"; 
};

/*
move flight > 4 to new carousel
*/
var moveToMin = function moveToMin(currentDate){
    currentDate.setHours( currentDate.getHours());
    var zero = date;
    var minutesSinceBeginning=0;
    if (currentDate>=zero) {
        minutesSinceBeginning = (currentDate-zero)/(1000*60);
    }
    var minimum = Math.min(...minuteLoadBigArmInit[minutesSinceBeginning]);
    var newCarousel = minuteLoadBigArmInit[minutesSinceBeginning].indexOf(minimum);//range 0-11
    return newCarousel;
};

/*
flightInfo: gantt task to be add to gantt
this function updates gantt, marker, line chart, bar chart, and increase flight count
*/
var addFlight = function addFlight(flightInfo){
    gantt.addTask(flightInfo, flightInfo.parent, 1);
    updateMarker(flightInfo.STA.replace(" ","T"));
    updateBarChart(new Date(flightInfo.STA));
    currentFlight++;
}

/*
returns flight info obj for gantt
*/
var propertyMap = function propertyMap(obj,newCarousel) {
    var newTask = {};

    newTask.start_date = ultimateDateFormatter(obj.STA);
    newTask.STA = ultimateDateFormatter(obj.STA);
    newTask.ETO_end = ultimateDateFormatter(obj.ETO_end);
    newTask.ETO_start = ultimateDateFormatter(obj.ETO_start);
    var duration  = (newTask.ETO_end-newTask.ETO_start)/(1000*60);

    newTask.id=obj.unique_id;
    newTask.text = obj.Flight_no;
    newTask.changed = obj.changed;
    newTask.duration = duration/60;
    newTask.open = true;

    newTask.dyn_belt = obj.Allocation; // range [5,10] [12,17]
    newTask.origin_belt = ultimateCarouselFormatter(obj.First_carousel_no);

    newTask.temp_belt=0;
    newTask.load = parseFloat(obj.Load);
    newTask.color = setColor(parseFloat(obj.Load));
    if(newCarousel==-1)newCarousel=parseInt(obj.Allocation,10)-1;// no user input
    var foundParent = findParentPre(newCarousel,newTask,initBigARMAllocation);
    if(foundParent==-1){//this carousel is full
        return -1;
    } else {
        initBigARMAllocation[foundParent-1].push(newTask);
        newTask.parent = foundParent;
        addLoadToMinuteArray(new Date(newTask.STA), duration, newTask.load, newCarousel);
        return newTask;
    }
};

//5 in a row
var findParentPre = function findParentPre(allocation,obj,arr) {
    try{
        if(checkAvailability(allocation*5, obj,arr)) {
            return allocation*5+1;
        } else if(checkAvailability(allocation*5+1, obj,arr)) {
            return allocation*5+2;
        } else if(checkAvailability(allocation*5+2, obj,arr)) {
            return allocation*5+3;
        } else if(checkAvailability(allocation*5+3, obj,arr)){
            return allocation*5+4;
        }else {
            return allocation*5+5;
        }
    } catch(err){
        console.log(err);
        return allocation*5+5;
    }

};

/*
checks all tasks in that gantt row, returns available==true if current flight does not collide with all flights on that row
*/
var checkAvailability = function checkAvailability(rowID,obj,arr) {
    var available = true;
    $.each( arr[rowID],  function(key, value) {

        var oldTaskST = ultimateDateFormatter(value.STA);
        var newTaskST = ultimateDateFormatter(obj.STA);
        var VALSTA = ultimateDateFormatter(value.STA);
        var OBJSTA = ultimateDateFormatter(obj.STA);

        if (ultimateDateFormatter(oldTaskST,value.duration)>OBJSTA && VALSTA<ultimateDateFormatter(newTaskST,obj.duration)) {
            available = false;
        }
    });
    return available;
};


var setColor = function setColor(load) {
    if (load<80&&load>0){return"#12aa1f !important";} // green
    else if (load>=80&&load<160){return"yellow !important";}
    else if (load>=160&&load<240){return"#76cde8 !important";} // blue
    else if (load>=240&&load<320){return"orange !important";}
    else if (load>=320){return"red !important";}
};

var updateLineChart = function updateLineChart(currentDate,chart){
    currentDate.setHours( currentDate.getHours() - 0.5);
    var zero = date;
    var minutesSinceBeginning=0;
    if (currentDate>=zero) {
        minutesSinceBeginning = (currentDate-zero)/(1000*60);
    }
    for(var g = point; g<minutesSinceBeginning;g++){// g is between current minute to minute of incoming task
        if (g<1440){
            calculateSTD(g,minutesSinceBeginning);
            if(chart==1)lineChart.data.datasets[0].data[g] = stdBigArmInit[g];
            if(chart==2)lineChart_min_old.data.datasets[0].data[g] = stdBigArmInit[g];
        }
    }
    point=minutesSinceBeginning;
    if(chart==1)lineChart.update();
    if(chart==2)lineChart_min_old.update();
    if(chart==3)lineChart_min_realtime.update();
};

var updateBarChart = function updateBarChart(currentDate){
    var zero = date;
    var minutesSinceBeginning=0;
    if (currentDate>=zero) {
        minutesSinceBeginning = (currentDate-zero)/(1000*60)-180;
    }
    for(var g = 0; g<12;g++){
        if(minuteLoadBigArmInit[minutesSinceBeginning]!=undefined){
            barChart.data.datasets[0].data[g] = minuteLoadBigArmInit[minutesSinceBeginning][g];
        }else{
            alert("No Data in DB, please check.")
            barChart.data.datasets[0].data[g] = 0;
        }
        
    }
    barChart.update();
}

var showALL = function showALL(){
    if(interval!=undefined){
        clearInterval(interval);
    }
    for(var i=0;i<60;i++){
        initBigARMAllocation[i]=[];
    }
    minuteLoadBigArmInit = [];
    $.each( data, function( key, value ) {
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
               console.log("newTask2 = -1 !!");
            }
        }
    });
    gantt.eachTask(
        function(task){
            if(task.id>60||!task.id){
                gantt.deleteTask(task.id);
            }
        });
    gantt.parse({"data":  mappedDataArr});

    for(var g = point; g<1440;g++){// g is between current minute to minute of incoming task
        if (g<1440){
            calculateSTD(g,1440);
        }
    }

    // lineChart.data.datasets[0].data = stdBigArmInit; // blue
    // lineChart.update();
    var today = gantt.getMarker(currentMarker);
    var date2 = new Date(date);
    today.start_date = date2.setDate(date2.getDate() + 1);
    gantt.updateMarker(currentMarker);	
};

$('#download_pdf').click(()=>{
    if (data.length > 0){
        html2canvas(document.querySelector("#gantt_get_plan")).then(canvas => {
        canvas.toBlob(function(blob) {
            var url = window.URL || window.webkitURL;
            var imgSrc = url.createObjectURL(blob);
            var img = new Image();
            var date_str = formatDate(date);
            img.src = imgSrc;
            
            img.onload = function () {
                var doc = new jsPDF("l", "mm", "a4");
                doc.addImage(img, 'JPEG', 12, 12, 273, 186);
                doc.save('BigARM-'+date_str + '.pdf');
        }; 
        });
        });
    }
    else{
        console.log("No data can be exported to PDF. Please select date, click BigARM Plan and then click Show All first.");
        alert("No data can be exported to PDF. Please select date, click BigARM Plan and then click Show All first.");
    }
});

$('#download_csv').click(()=>{
    if (data.length > 0){
        data_csv = data;
        // var temp = data_csv.map({ Allocation, ETO_end, ETO_start, Flight_no, ID, Load, STA, unique_id } => { Allocation, ETO_start, ETO_end, Flight_no, ID, Load, STA, unique_id  });

        // temp_csv = data_csv.map(function(x) {
        //     return {Allocation:x.Allocation,
        //             ETO_end:x.ETO_start,
        //             ETO_start : x.ETO_end,
        //             Flight_no : x.Flight_no,
        //             ID : x.ID,
        //             Load : x.Load,
        //             STA : x.STA,
        //             unique_id : x.unique_id,
        //         }
        //      });
        cvs_data_csv = jsonToCSV(data_csv);
        if(cvs_data_csv!=""){
            var csvContent = "data:text/csv;charset=utf-8," + cvs_data_csv;
            var encodedUri = encodeURI(csvContent);
            var link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            var date_str = formatDate(date);
            link.setAttribute("download", 'BigARM-'+date_str+".csv");
            document.body.appendChild(link);
            link.click();
			document.body.removeChild(link);
        
    }
    }
    else{
        console.log("No data can be exported to CSV. Please select date and then click BigARM Plan first.");
        alert("No data can be exported to CSV. Please select date and then click BigARM Plan first.");
    }
});

$('#close_iniplan').click(()=>{
  changeinitPlan.style.display = "none";
});

$('#confirm_allocation').click(()=>{
    var newCarousel = document.getElementById("mySelect").selectedIndex;
    var newTask = propertyMap(data[currentFlight],newCarousel);
    if(newTask==-1){//propertymap says carousel is full during user input
        var message = "The manually chosen carousel for this flight is full, please choose a different carousel";
        showModal(data[currentFlight],message);
        clearInterval(interval); 
    } else{ 
        newTask.dyn_belt=document.getElementById("mySelect").selectedIndex+2;
        addFlight(newTask);
        modal.style.display = "none";
        if(interval!=undefined){
            interval = setInterval(function(){ 
                newFlight(); 
            }, 600); //40
        } 
    }
});


function formatDate(date) {
    var monthNames = [
      "January", "February", "March",
      "April", "May", "June", "July",
      "August", "September", "October",
      "November", "December"
    ];
  
    var day = date.getDate();
    var monthIndex = date.getMonth();
    var year = date.getFullYear();
    return day + '-' + monthNames[monthIndex] + '-' + year;
}

var ultimateDateFormatter = function ultimateDateFormatter(original_date, hours){
    var new_date;
    try{
        if(typeof(original_date)=="string"){
            if(original_date.length<20){ // 2019-10-01 00:00
                var is_safari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
                if (is_safari){
                    var temp = new Date(original_date.replace(" ","T"));
                    temp.setHours(temp.getHours()-8);
                    new_date = temp;
                } else{
                    new_date = new Date(original_date);
                }
            } else{
                new_date = new Date(original_date);
                new_date.setHours(new_date.getHours()-8);
            }
    
        } else if(typeof(original_date)=="object"){
            new_date = new Date(original_date);
        } else{
            throw "Not a date format we know: " + original_date;
        }
        if(hours){
            new_date.setMinutes(new_date.getMinutes()+hours*60);
        }
    } catch(err){
        new_date = new Date(original_date);
        if(hours){
            new_date.setMinutes(new_date.getMinutes()+hours*60);
        }
        console.log(err);
    }
    return new_date;
}

var ultimateCarouselFormatter = function ultimateCarouselFormatter(original_carousel) { // [1-12]
    var carousel;
    try{
        if (date <= new Date("2019-06-19")) {
            carousel = parseInt(original_carousel, 10)+1;
        } else {
            if(original_carousel!=0){
                carousel = parseInt(original_carousel,10)+4; // range [5,10] [12,17]
                if (carousel === 16) {
                    carousel = 17;
                }
                if (carousel === 15) {
                    carousel = 16;
                }
                if (carousel === 14) {
                    carousel = 15;
                }
                if (carousel === 13) {
                    carousel = 14;
                }
                if (carousel === 12) {
                    carousel = 13;
                }
                if (carousel === 11) {
                    carousel = 12;
                }
            } else{
                carousel="-";
            }
        }
    } catch(err){
        console.log(err);
    }
    return carousel;
}

