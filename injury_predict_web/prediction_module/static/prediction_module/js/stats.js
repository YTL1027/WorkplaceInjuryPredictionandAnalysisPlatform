$(document).ready(function () {
    getSummary();
    init_charts();
    setup_table();
    setbarchart();
});

function setup_table() {
  $('#scroll_table').DataTable({
  "scrollY": "30vh",
  "scrollCollapse": true,
  });
}

function setIRdetails(data) {
    document.getElementById("cw_mean").innerHTML = Math.round(data.cw_mean * 100000) / 1000 + '%\n';
    document.getElementById("cw_std").innerHTML = Math.round(data.cw_std * 100000) / 1000 + '%\n';
    document.getElementById("cw_75_pct").innerHTML =Math.round(data.cw_75_pct * 100000) / 1000 + '%\n';
    document.getElementById("cw_time").innerHTML = ((data.cw_avg_time / 3600) % 24).toFixed(2) + " hours";
    document.getElementById("cw_high_ir_month").innerHTML = data.cw_high_ir_month;

    document.getElementById("ncw_mean").innerHTML = Math.round(data.ncw_mean * 100000) / 1000 + '%\n';
    document.getElementById("ncw_std").innerHTML =  Math.round(data.ncw_std * 100000) / 1000 + '%\n';
    document.getElementById("ncw_75_pct").innerHTML = Math.round(data.ncw_75_pct * 100000) / 1000 + '%\n';
    document.getElementById("ncw_time").innerHTML = ((data.ncw_avg_time / 3600) % 24).toFixed(1) + " hours";
    document.getElementById("ncw_high_ir_month").innerHTML = data.ncw_high_ir_month;

}

function getSummary() {

    $.ajax({
        type: "GET",
        url: "/api/prediction/summary/",
        success: function (data) {
            setIRdetails(data);

            let total_claims = data.cw_count + data.non_cw_count;

            const hour = ((data.avg_time / 3600) % 24).toFixed(2);
            $("#prediction-data").html(total_claims);
            $("#cw-data").html(data.cw_count);
            $("#no-cw-data").html(data.non_cw_count);
            $("#emp-data").html(hour + " hrs");

        },
        error: function (data) {
        },
    });
}

function init_charts() {
  var chartDom = document.getElementById("offwork_gap_pie_chart");
  var myChart = echarts.init(chartDom);
  var option;

  option = {
    title: {
      text: '2020 Offwork Gap',
      left: 'center'
    },
    legend: {
      orient: 'vertical',
      left: 'right'
    },
    toolbox: {
      show: true,
      feature: {
        mark: { show: true },
        dataView: { show: true, readOnly: false },
        restore: { show: true },
        saveAsImage: { show: true }
      }
    },
    series: [
      {
        name: 'Nightingale Chart',
        type: 'pie',
        center: ['50%', '50%'],
        data: [
          { value: 24.36, name: 'offday 0' },
          { value: 22.72, name: 'offday 1' },
          { value: 12.22, name: 'offday 2' },
          { value: 8.36, name: 'offday 3' },
          { value: 6.36, name: 'offday 4' },
          { value: 4.87, name: 'offday 5' },
          { value: 3.07, name: 'offday 6' },
          { value: 2.64, name: 'offday 7' },
          { value: 1.53, name: 'offday 11' },
          { value: 1.53, name: 'offday 10' },
          { value: 1.48, name: 'offday 8' },
          { value: 1.15, name: 'offday 14' },
          { value: 1.06, name: 'offday 9' },
          { value: 1.05, name: 'offday 13' },
          { value: 1.02, name: 'offday 12' }
        ]
      }
    ]
  };

  myChart.setOption(option);
  
}

function setbarchart() {
  var chartDom = document.getElementById("occupataion_place_bar_chart");
  var myChart = echarts.init(chartDom);
  var option;

  option = {
    title: {
        text: '2020 18102 Occupation Distribution',
        left: 'center'
      },
    xAxis: {
      type: 'category',
      data: ['SELECTOR', 'DRIVER', 'WAREHOUSE ASSOCIATE ', 'WAREHOUSEMAN', 'TRIMMER II', 'PRODUCTION WORKER', 'WAREASSOC',
      'ASSEMBLER', 'FULFILLMENT CEN', 'LABORER ', 'WAREHOUSEMAN', 'MASTER BUTCHER', 'MENTAL HEALTH TECHNICIAN', 'POLICE',
      'UTILITY GROUP II', 'C N A', 'Cleaner', 'CUSTODIAN', 'FORKLIFT', 'FORKLIFT OPERAT', 'GENERAL LABORER']
    },
    yAxis: {
      type: 'value'
    },
    toolbox: {
      show: true,
      feature: {
        mark: { show: true },
        dataView: { show: true, readOnly: false },
        restore: { show: true },
        saveAsImage: { show: true }
      }
    },
    series: [
      {
        data: [41, 8, 8, 8, 7, 5, 5, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2],
        type: 'bar',
        showBackground: true,
        backgroundStyle: {
          color: 'rgba(180, 180, 180, 0.2)'
        }
      }
    ]
  };

  myChart.setOption(option);
}