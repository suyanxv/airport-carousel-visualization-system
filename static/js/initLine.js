var drawLineChart = function drawLineChart(id,chart) {

    var canvas = document.getElementById(id);
    var chartLabels = [];
    for(var i = 0;i<1500;i++){
        chartLabels[i] = "";
    }

    var dataFirst = {
        label: "BigARM Initial Plan",
        fill: false,
        lineTension: 0.4,
        backgroundColor: "#BEE4BE",
        borderColor: "#BEE4BE",
        borderCapStyle: 'butt',
        borderDash: [],
        borderDashOffset: 0.0,
        borderJoinStyle: 'miter',
        pointBorderColor: "#BEE4BE",
        pointBackgroundColor: "#fff",
        pointBorderWidth: 0,
        pointHoverRadius: 0,
        pointHoverBackgroundColor: "#BEE4BE",
        pointHoverBorderColor: "#BEE4BE",
        pointHoverBorderWidth: 2,
        pointRadius: 0,
        pointHitRadius: 0,
        // data: [65, 59, 80, 30, 56, 55, 40],
        data: [],
        borderWidth: 3
    };

    var dataSecond = {
        label: "BigARM Initial Plan", 
        fill: false,
        lineTension: 0.4,
        backgroundColor: "#4286f4",
        borderColor: "#4286f4",
        borderCapStyle: 'butt',
        borderDash: [],
        borderDashOffset: 0.0,
        borderJoinStyle: 'miter',
        pointBorderColor: "#4286f4",
        pointBackgroundColor: "#fff",
        pointBorderWidth: 0,
        pointHoverRadius: 0,
        pointHoverBackgroundColor: "#4286f4",
        pointHoverBorderColor: "#4286f4",
        pointHoverBorderWidth: 2,
        pointRadius: 0,
        pointHitRadius: 0,
        data: [],
        borderWidth: 3
    };

    var dataThird = {
        label: "BigARM Initial Plan - Existing", 
        fill: false,
        lineTension: 0.4,
        backgroundColor: "#706e68",
        borderColor: "#706e68",
        borderCapStyle: 'butt',
        borderDash: [],
        borderDashOffset: 0.0,
        borderJoinStyle: 'miter',
        pointBorderColor: "#706e68",
        pointBackgroundColor: "#fff",
        pointBorderWidth: 0,
        pointHoverRadius: 0,
        pointHoverBackgroundColor: "#706e68",
        pointHoverBorderColor: "#706e68",
        pointHoverBorderWidth: 2,
        pointRadius: 0,
        pointHitRadius: 0,
        data: [],
        borderWidth: 3
    };

    var data = {
        labels: chartLabels,
        datasets: [dataFirst,dataSecond,dataThird]
    };
    
    var option = {
        showLines: true,
    };
    if(chart==1){
        lineChart = Chart.Line(canvas,{
            data:data,
            options: {
                legend: {
                    display: false
                },
                scales: {
                    xAxes: [{
                                gridLines: {
                                    display:false
                                },
                                ticks: {
                                    display: false
                                }
                            }],
                    yAxes: [{
                                gridLines: {
                                    display:false
                                },
                                ticks: {
                                    display: true
                                }
                            }]
                    }
            }
        });
    } else if(chart==2){
        lineChart_min_old = Chart.Line(canvas,{
            data:data,
            options: {
                legend: {
                    display: false
                },
                scales: {
                    xAxes: [{
                                gridLines: {
                                    display:false
                                },
                                ticks: {
                                    display: false
                                }
                            }],
                    yAxes: [{
                                gridLines: {
                                    display:false
                                },
                                ticks: {
                                    display: true
                                }
                            }]
                    }
            }
        });
    }  else if(chart==3){
        lineChart_min_realtime = Chart.Line(canvas,{
            data:data,
            options: {
                legend: {
                    display: false
                },
                scales: {
                    xAxes: [{
                                gridLines: {
                                    display:false
                                },
                                ticks: {
                                    display: false
                                }
                            }],
                    yAxes: [{
                                gridLines: {
                                    display:false
                                },
                                ticks: {
                                    display: true
                                }
                            }]
                    }
            }
        });
    }
};