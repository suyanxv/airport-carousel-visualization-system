var addLoadToMinuteArray = function addLoadToMinuteArray(getStartDate, duration, load, allocation1) {
    var zero = date;
    var end = ultimateDateFormatter(date,31);
    var minutesSinceBeginning1;
    if ((getStartDate>=zero) && (getStartDate<=end)) { // after zero
        minutesSinceBeginning1 = (getStartDate-zero)/(1000*60)-180;
        for (var i = 0; i < duration; i++){
            if(minuteLoadBigArmInit[minutesSinceBeginning1+i]==null){ //  initialize 
                minuteLoadBigArmInit[minutesSinceBeginning1+i] = new Array(12);
                for(var c=0;c<12;c++){
                    minuteLoadBigArmInit[minutesSinceBeginning1+i][c]=0;
                }
            }
            minuteLoadBigArmInit[minutesSinceBeginning1+i][allocation1] += load; // load/duration; 
        }
    }
};

var calculateSTD = function calculateSTD(currentMinute,minutesSinceBeginning){ // after addLoadToMinuteArray
    var array = [];
    for(var i = 0;i<60;i++){
            if(minuteLoadBigArmInit[minutesSinceBeginning-i]==null){
                minuteLoadBigArmInit[minutesSinceBeginning-i] = [0,0,0,0,0,0,0,0,0,0,0,0];
            }
            for(var c =0;c<12;c++){
                array.push(minuteLoadBigArmInit[minutesSinceBeginning-i][c]);//12*60=720
            }
    }
    if(i<1440)
            stdBigArmInit.push(math.std(array));
    return math.std(array);
};

var calculateALLSTD = function calculateALLSTD(chart,status){
    var array = [];
    var array2 =[];
    for(var i=0;i<1440;i++){
        var temp=[];
        var temp2=[];
        for(var j=0;j<45;j++){ //window
            if(minuteLoadBigArmInit[i+j]==null){
                for(var k=0;k<12;k++){
                    temp.push(0);
                }
            } else{
                $.each( minuteLoadBigArmInit[i+j], function( key, value ) {
                    temp.push(value);
                });
            }
            if(temp_minuteLoadBigArmInit[i+j]==null){
                for(var p=0;p<12;p++){
                    temp2.push(0);
                }
            } else{
                $.each( temp_minuteLoadBigArmInit[i+j], function( key, value ) {
                    temp2.push(value);
                });
            }
                
        }
        array.push(math.std(temp));
        array2.push(math.std(temp2));
    }
    if(chart==1){
        lineChart.data.datasets[0].data=array;
        lineChart.update();
    } else if(chart==2){
        lineChart_min_old.data.datasets[0].data=array;
        lineChart_min_old.data.datasets[1].data=array2;
        lineChart_min_old.update();
    } else if(chart==3){
        if(status==0){
            lineChart_min_realtime.data.datasets[0].data=array2;
        }
        lineChart_min_realtime.data.datasets[1].data=array2;
        lineChart_min_realtime.data.datasets[2].data=array;
        lineChart_min_realtime.update();
    }
    return  array;
}
