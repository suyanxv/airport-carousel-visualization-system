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
            {value: 0, text: '1'},
            {value: 1, text: '2'},
            {value: 2, text: '3'},
            {value: 3, text: '4'},
            {value: 4, text: '5'},
            {value: 5, text: '6'},
            {value: 6, text: '7'},
            {value: 7, text: '8'},
            {value: 8, text: '9'},
            {value: 9, text: '10'},
            {value: 10, text: '11'},
            {value: 11, text: '12'},
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
    $('#get_plan,#update_info').click(function () {
        date = new Date();
        data={};
        rtdata={};
        cvs_data="";
        updateList=[];
        showModalBoolean = false;
        mappedDataArr = [];
        minuteLoadBigArmInit = [];
        stdBigArmInit = []
        if (lineChart!=null){
           lineChart.data.datasets[0].data = stdBigArmInit; // blue
           lineChart.update();
        }
        if (barChart!=null){

        }
        initBigARMAllocation = new Array(48);
        for(var i=0;i<48;i++){
            initBigARMAllocation[i]=[];
        }
        if(interval!=null){
            clearInterval(interval);
        }
        interval=null;
        currentFlight=0;
        point = 0;

        // var date_str;
        if( $(this).attr('id') === 'get_plan'){
            var input = $('#dtp_input2');
            date_str = input.attr('value');
            localStorage.setItem('my_form_date', date_str);
            main_body.fig_ok = false;
        }else{
            date_str = localStorage.getItem('my_form_date');
        }

        datetime_str=new Date(date_str+" 00:00:00");
        console.log("datetime_str",date_str);

        if (date_str === '') {
            alert('Please search after inputting the date.');
        } else {
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
                        data = response.Details;
                        date = new Date(date_str);
                        date.setHours(0,0,0,0);
                        var date2 = new Date(date); 
                        //document.getElementById("get_initial_bigarm_plan").disabled = false;
                        //document.getElementById("get_initial_bigarm_plan_next").disabled = false;
                        //document.getElementById("stop_auto").disabled = false;
                        document.getElementById("show_all_flights").disabled = false;
                        if(gantt.getTaskByTime().length>48||date.getTime()!=new Date().getTime()){
                            gantt.clearAll();
                            gantt.config.start_date = new Date(date2.setHours(date2.getHours()-2));
                            gantt.config.end_date = new Date(date2.setHours(date2.getHours()+28));
                            gantt.parse(bj);
                            gantt.render();
                            if (currentMarker!=null){
                                var date_to_str = gantt.date.date_to_str(gantt.config.task_date);
                                currentMarker = gantt.addMarker({ 
                                start_date: date,
                                css: "today", 
                                title:date_to_str(date)
                            });}
                            if(barChart!=null){
                                barChart.destroy();
                            }
                
                        } else{
                            initBigARMGantt();
                        }
                        $("#description").show();
                        $("#flightInfo").show();
                        drawBarChart();
                        alert("Data loaded");

                    } else {
                        alert(response.Msg+" error in response");
                    }


                },
                error: function (error) {
                    alert(error.message+" no data found in db");
                }
            });
        }


    });

    function formatDate2(date_str) {
        var res = date_str.split("/");
        return res[1]+'/'+res[0]+'/'+res[2];
    }

    var sort = function sort(data){

        for(var i = 0; i < data.length; i++) {
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

    function jsonToCSV(objArray) {
        var array = typeof objArray != 'object' ? JSON.parse(objArray) : objArray;
        var str = '';
		var date2 = new Date(date);
        str += Object.keys(array[0]);
        str += '\r\n';
		if (date2 <= new Date("2019-04-14")){
			for (var i = 0; i < array.length; i++) {
				var line = '';
				for (var index in array[i]) {
					if (line != '') line += ',';
					if(index=='Allocation') 
						array[i][index]=parseInt(array[i][index],10)+1;
					line += array[i][index];
				}
				str += line + '\r\n';
			}
		} else {
			for (var i = 0; i < array.length; i++) {
				var line = '';
				for (var index in array[i]) {
					if (line != '') line += ',';
					if(index=='Allocation') 
						array[i][index]=parseInt(array[i][index],10)+1;
					line += array[i][index];
				}
				str += line + '\r\n';
			}
		}
        return str;
    }
    
    function getHeader(h1) {
        switch(h1){
            case "SCH_START":
                return "STA";
            default:
                return h1;
        }
    }
   $('#confirm_disable_carousel').click(function () {
	var carousel_no = document.getElementById('selected_carousel').selectedIndex;
        $.ajax({
            method: 'POST',
            dataType: 'json',
            url: '/disablecarousel',
            data: {
                disable_carousel:parseInt(carousel_no,10) + 1,
		disabletime_S:document.getElementById('disabletime_S').value,
		disabletime_E:document.getElementById('disabletime_E').value,
                initialize: true
            },
            success: function (response) {
                if (!response.Error) {
                    console.log(response.Details);
                    alert('disale finish!')
                    //https://vitalets.github.io/x-editable/
                } else {
                    alert('1'+response.Msg)
                }
            },
            error: function (error) {
                alert('2'+error.message)
            }
        })
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
    $('.form_date').datetimepicker({
        // language:  'fr',
        weekStart: 0,
        todayBtn: 1,
        autoclose: 1,
        todayHighlight: 1,
        startView: 2,
        minView: 2,
        forceParse: 0,
        format: 'yyyy-mm-dd'
    });
