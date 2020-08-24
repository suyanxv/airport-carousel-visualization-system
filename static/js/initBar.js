var drawBarChart = function drawBarChart(){

    var canvas = document.getElementById('myBarChart');
    canvas.style.display='none';
    // var modalCanvas = document.getElementById('modalBarChart');

    Chart.defaults.global.defaultFontFamily = "Lato";
    Chart.defaults.global.defaultFontSize = 20;

  var dataSecond = {
        label: 'Total Load',
        data: [],
        backgroundColor: '#337ab7',
        borderWidth: 2,
        //yAxisID: "y-axis-second"
  };

  var chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    legend: {
           display: false
    },
    scales: {
      xAxes: [{
        barPercentage: 0.5,
        barThickness: 40,
        maxBarThickness: 50,
        minBarLength: 2,
        gridLines: {
          display: false
            },
          ticks: {
              display: true,
              fontSize:20
          },
     scaleLabel: {
                display: true,
                labelString: "Carousel Number",
                fontcolor:"black"

            }
      }],
      yAxes: [{
           //id: "y-axis-second",
            gridLines: {
                display: true
            },
            ticks: {
                display: true,
                fontSize:20,
        	            min:0,
        	            max:800,
        	            stepSize:200
            },
        		scaleLabel: {
                display: true,
                labelString: "Carousel Loading",
                fontcolor:"black"
            }
          }]
        }
	  };

    var date2 = new Date(date);


    var data3= {
        labels: ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
        datasets: [dataSecond]
      };

    var data4 = {
        labels: ["5", "6", "7", "8", "9", "10", "12", "13", "14", "15", "16", "17"],
        datasets: [dataSecond]
    };

    if (date2 <= new Date("2019-06-19")) {
        barChart = new Chart(canvas, {
            type: 'bar',
            data: data3,
            options: chartOptions
        });
    } else {
        barChart = new Chart(canvas, {
            type: 'bar',
            data: data4,
            options: chartOptions
        });
    }
       barChart.canvas.parentNode.style.width = '1000px';
       barChart.canvas.parentNode.style.height = '300px';
    // modalBarChart = new Chart(modalCanvas, {
    //     type: 'bar',
    //     data: data3,
    //     options: chartOptions
    // });

}
