//$(function () {
//https://vitalets.github.io/x-editable/
$.fn.editable.defaults.display = false;
//use this to disable xeditable's changing value because we need to use vue to change it.
var x_editable_config = {
    format: 'dd-M-yyyy hhii',
    viewformat: 'dd-M-yyyy hhii',
    datetimepicker: {
        weekStart: 0,
        todayHighlight: 1,
    },
    placement: 'bottom',
    ajaxOptions: {
        type: 'post',
        contentType: 'application/json',
        dataType: 'json'
    },
    params: function (params) {
        //originally params contain pk, name and value
        var row = $('#' + params.pk);
        let ajax_data = {
            Type: params.name === 'Chock_time' ? 'Time' : 'Plan',
            ID: params.pk,
            Date: localStorage.getItem('my_form_date'),
            Flight_no: row.children('td').eq(0).text(),
            Index: Number.parseInt(row.children('th').eq(0).text()) - 1,
            Update: {
                "Item_name": params.name,
                "New_value": params.value
            }
        };
        return JSON.stringify(ajax_data);
    },
    success: function (response, newValue) {
        if ((!response.Error) && response.Update_plan) {
            if (Number(response.Plan_count) === main_body.details.length) {
                for (var i = 0; i < main_body.details.length; i++) {
                    main_body.details[i].Allocation = response.Plans[i].Allocation
                }
            } else {
                alert('length false')
            }
        }
    },
    url: "/update",
    source: [
        { value: 0, text: '1' },
        { value: 1, text: '2' },
        { value: 2, text: '3' },
        { value: 3, text: '4' },
        { value: 4, text: '5' },
        { value: 5, text: '6' },
        { value: 6, text: '7' },
        { value: 7, text: '8' },
        { value: 8, text: '9' },
        { value: 9, text: '10' },
        { value: 10, text: '11' },
        { value: 11, text: '12' },
    ]
};

Vue.component('custom-input', {
    props: ['index', 'data_type', 'data_pk', 'data_name', 'data_title', 'my_data'],
    template: " <a href='#' :index='index' :data-type='data_type' :data-pk='data_pk' :data-name='data_name' :data-title='data_title'> {{ my_data }} </a> ",
    mounted: function () {
        $(this.$el).editable(x_editable_config);
        $(this.$el).on("save", function (e, params) {
            var index = $(this).attr('index');
            var key_name = $(this).attr('data-name');
            if (key_name === "Allocation") {
                main_body.details[Number(index)][key_name] = Number(params.newValue);
            } else {
                main_body.details[Number(index)][key_name] = moment(new Date(params.newValue)).format('DD-MMM-YYYY HHmm');
            }

        });
    },
    beforeDestroy: function () {
        $(this.$el).editable('hide').editable('destroy');
    }
});

var main_body = new Vue({
    el: '#main_body',
    data: {
        show: false,
        query_date: '0000-00-00',
        fig_ok: false,
        plan_fig: '',
        details: [
            {
                "Chock_time": "00-Jan-0000 0000",
                "ETO_end": "00-Jan-0000 0000",
                "Flight_no": "oo 000",
                "ID": "000000000000000000000000",
                "Load": 0,
                "Allocation": 0,
                "STA": 0
            },
        ]
    },
    mounted: function () {

    }
});


// For user role control
$('#get_plan,#update_info').click(function () {
    date = new Date();
    data = {};
    rtdata = {};
    cvs_data = "";
    updateList = [];
    showModalBoolean = false;
    mappedDataArr = [];
    minuteLoadBigArmInit = [];
    stdBigArmInit = []

    if (lineChart != null) {
        lineChart.data.datasets[0].data = stdBigArmInit; // blue
        lineChart.update();
    }
    if (barChart != null) {

    }
    initBigARMAllocation = new Array(60);
    for (var i = 0; i < 60; i++) {
        initBigARMAllocation[i] = [];
    }
    if (interval != null) {
        clearInterval(interval);
    }
    interval = null;
    currentFlight = 0;
    point = 0;
	//// Disable the button for 20 seconds
	// var enableButton = function(ele) {
		// $(ele).removeAttr("disabled");
	// }
	// var that = this;
    // $(this).prop("disabled", true);
	// setTimeout(function() { enableButton(that) }, 20000);
    // var date_str;
    if ($(this).attr('id') === 'get_plan') {
        var input = $('#dtp_input2');
        date_str = input.attr('value');
        localStorage.setItem('my_form_date', date_str);
        main_body.fig_ok = false;
		
    } else {
        date_str = localStorage.getItem('my_form_date');
    }

    if (date_str === '') {
        alert('Please select the date first.');
    } else {
        $("#get_plan").prop("disabled", true);   // Disable button after POST request
        $.ajax({			
            method: 'POST',
            dataType: 'json',
            url: '/get_plan',
            data: {
                date: date_str,
                initialize: false
            },
            success: function (response) {				
                if (!response.Error) {
                    main_body.show = true;
                    main_body.query_date = date_str;
                    main_body.details = response.Details;
                    data = adduniqueid(response.Details);
                    date = new Date(date_str);
                    date.setHours(0, 0, 0, 0);
                    //document.getElementById("get_initial_bigarm_plan").disabled = false;
                    //document.getElementById("get_initial_bigarm_plan_next").disabled = false;
                    //document.getElementById("stop_auto").disabled = false;
                    document.getElementById("show_all_flights").disabled = false;
					document.querySelector("#displayButton").disabled = false; //Enable the gradual display
                    document.getElementById("realtime").disabled = false;
                    document.getElementById("simulation").disabled = false;
                    if (gantt.getTaskByTime().length > 60 || date.getTime() != new Date().getTime()) {
                        gantt.clearAll();
                        gantt.config.start_date = ultimateDateFormatter(date);
                        gantt.config.end_date = ultimateDateFormatter(date,31)
                        if (date >= new Date("2019-06-20")) gantt.parse(bj2);
                        else gantt.parse(bj);
                        if (currentMarker != null) {
                            var date_to_str = gantt.date.date_to_str(gantt.config.task_date);
                            currentMarker = gantt.addMarker({
                                start_date: date,
                                css: "today",
                                title: date_to_str(date)
                            });
                        }
                        gantt.config.show_markers = false;
                        gantt.render();
                        if (barChart != null) {
                            barChart.destroy();
                        }

                    } else {
                        initBigARMGantt();
                    }
                    $("#description").show();
                    $("#flightInfo").show();
                    drawBarChart();
                    changecarousel_action = "Action Log Successful!!" ;
                    alert("The allocation plan is generated!");
					$("#get_plan").prop("disabled", false); //enable button once data transmitted 
                    document.getElementById("realtime").disabled = false;
                } else {
                    alert(response.Msg + " error in response");
					$("#get_plan").prop("disabled", false); //enable button once data transmitted 
                }

            },
            error: function (error) {
                alert(error.message + " no data found in db");
				$("#get_plan").prop("disabled", false); //enable button once data transmitted 
            }
        });
    }


});

var adduniqueid = function adduniqueid(data){
    data.forEach(function(value){
        var day = ultimateDateFormatter(value.STA).getDate();
        value.unique_id = value.Flight_no+" "+day;
        value.changed = false;
    });
    return data;
}

function toTimestamp(strDate){
    var datum = Date.parse(strDate);
    return datum/1000;
}

function jsonToCSV(objArray) {         
	var tmp = typeof objArray != 'object' ? JSON.parse(objArray) : objArray;
    var array = JSON.parse(JSON.stringify(tmp));
    //var array = JSON.padduniqueidarse(tmp);

    array = array.map(function(x) {
        return {Allocation:x.Allocation,
                ETO_start:x.ETO_start,
                ETO_end : x.ETO_end,
                Flight_no : x.Flight_no,
                ID : x.ID,
                Load : x.Load,
                STA : x.STA,
                unique_id : x.unique_id,
                //Stand:x.stand,
                //AircraftType:x.AircraftType,
            }
            });

    var str = '';
    var date_today = new Date(date);
    str += Object.keys(array[0]);
    str += '\r\n';

    for (var i = 0; i < array.length; i++) {
        var line = '';
        if(array[i]['Allocation']==-1){
            continue;
        }
        for (var index in array[i]) {
            if (line != '') line += ',';
            if (index == 'Allocation') {
                array[i][index] = ultimateCarouselFormatter(array[i][index]);
            }
            if (index == 'ETO_start'){
                var temp4 = ultimateDateFormatter(array[i][index]);
                array[i][index] = temp4.getFullYear()  + "-" + ("0"+(temp4.getMonth()+1)).slice(-2) +"-"+("0" + temp4.getDate()).slice(-2) + " " + ("0" + temp4.getHours()).slice(-2) + ":" + ("0" + temp4.getMinutes()).slice(-2)+":00";
            }
            if (index == 'ETO_end'){
                var temp5 = ultimateDateFormatter(array[i][index]);
                array[i][index] = temp5.getFullYear()  + "-" + ("0"+(temp5.getMonth()+1)).slice(-2) +"-"+("0" + temp5.getDate()).slice(-2) + " " + ("0" + temp5.getHours()).slice(-2) + ":" + ("0" + temp5.getMinutes()).slice(-2)+":00";
            }
            if (index == 'STA'){
                var temp6 = ultimateDateFormatter(array[i][index]);
                array[i][index] = temp6.getFullYear()  + "-" + ("0"+(temp6.getMonth()+1)).slice(-2) +"-"+("0" + temp6.getDate()).slice(-2) + " " + ("0" + temp6.getHours()).slice(-2) + ":" + ("0" + temp6.getMinutes()).slice(-2)+":00";
            }
            // if (!array[i][index]) {
            //     array[i][index] = '';
            // }
            line += array[i][index];
        }
        str += line + '\r\n';
    }
    return str;
}


function getHeader(h1) {
    switch (h1) {
        case "SCH_START":
            return "STA";
        default:
            return h1;
    }
}

$('#submit_upload').click(function (evt) { //Submit closure schedule
    evt.preventDefault();
    console.log("Start Upload process.");
    var form_data = new FormData($('#plan_upload_form')[0]);
    form_data.append('initialize', true);
    upload_file = document.getElementById("file").value;
    var upload_filename = upload_file.split('.')[0];
    var upload_extension = upload_file.split('.')[1];
    allow_extension = ['csv','CSV'];
    upload_status = document.getElementById("upload_status");
    
    if (upload_file == ""){ //if no select file
        upload_status.innerHTML = '<b style="color:red;">Please Select a file to upload./b>'; }
    else if($.inArray(upload_extension, allow_extension) < 0){
        console.log("File Extension not correct.");
        alert("You can only upload CSV file to server.");
    }
    else{
        console.log('User uploaded ' + form_data); 
        $.ajax({
            type: 'POST',
            contentType: false,
            cache: false,
            processData: false,
            dataType: 'json',
            url: '/upload_file',
            data: form_data,
            success: function (response) {
                if (!response.Error) {
                    main_body.show = true;
                    main_body.query_date = date_str;
                    main_body.details = response.Details;
                    console.log("New Data received")
                    upload_status.innerHTML = "<b>File Upload Successful</b>"
                } else {
                    console.log("File uploaded but error")
                    upload_status.innerHTML = '<b style="color:red;">Upload file fail</b>'
                }
            },
            error: function (error) {
                alert('File Upload Failed. please check your file.\nError : ' + error.message)
            }
        });
        document.getElementById("get_plan").disabled = true;
    }
});

$('#confirm_disable_carousel').click(function () { //Submit closure schedule
    var carousels = [];
    var disabletime_S = [];
    var disabletime_E = [];

    $('select[name="selected_carousel[]"]').each((i, elm) => {
      carousels = carousels.concat(parseInt(elm.value, 10));});
    $('input[name="disabletime_S[]"]').each((i, elm) => {
      disabletime_S = disabletime_S.concat(elm.value);});
    $('input[name="disabletime_E[]"]').each((i, elm) => {
      disabletime_E = disabletime_E.concat(elm.value);});
    
    for (i=0; i < disabletime_S.length; i++){
        if (disabletime_E[i] < disabletime_S[i] || disabletime_S == "" || disabletime_E == ""){
            alert("Date Enter Error, please check!");
            disablecarousel.style.display = "block";
        }
        else{
            $.ajax({
                method: 'POST',
                dataType: 'json',
                url: '/disablecarousel',
                data: {
                    query_time: date_str,
                    disable_carousel: carousels,
                    disabletime_S: disabletime_S,
                    disabletime_E: disabletime_E,
                    initialize: true
                },
                success: function (response) {
                    if (!response.Error || response.length > 0) {
                        console.log(response);
                        console.log("Carousel :" + carousels )
                        console.log("Start Date :" + disabletime_S )
                        console.log("End Date :" + disabletime_E )
                        //initBigARMGantt();
                        //showALL();
                        //alert('Carousel disabled and flight re-allocations have been done!');
                        //https://vitalets.github.io/x-editable/
                    } else {
                        console.log("Not selected Date yet!!")
                    }
                },
                error: function (error) {
                    alert('Data response error!!' + error.message)
                }
            })
        }
    }
});

$('#init_plan').click(function () {
    var date_str = localStorage.getItem('my_form_date');
    $.ajax({
        method: 'POST',
        dataType: 'json',
        url: '/init_plan',
        data: {
            date: date_str,
            initialize: true
        },
        success: function (response) {
            if (!response.Error) {
                main_body.show = true;
                main_body.query_date = date_str;
                main_body.details = response.Details;
                alert('Init finish!')
                //https://vitalets.github.io/x-editable/
            } else {
                alert(response.Msg)
            }
        },
        error: function (error) {
            alert(error.message)
        }
    })
});

////https://www.malot.fr/bootstrap-datetimepicker/demo.php

var myDate = new Date();
$('.form_date').datetimepicker({
    // language:  'fr',
    format: 'yyyy-mm-dd',
    endDate: myDate,
    weekStart: 0,
    todayBtn: 1,
    autoclose: 1,
    todayHighlight: 1,
    startView: 2,
    minView: 2,
    forceParse: 0,
});


// --------------------------------------------- NOT USED -------------------------------------------------------------------
var sort = function sort(data) {

    for (var i = 0; i < data.length; i++) {
        var temp = data[i];
        var j = i - 1;
        while (j >= 0 && data[j].STA > temp.STA) {
            data[j + 1] = data[j];
            j--;
        }
        data[j + 1] = temp;
    }
    return data;
}
