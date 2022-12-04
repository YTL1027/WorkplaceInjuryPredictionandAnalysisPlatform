const date_options = {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'};
const modal = $('#log-modal');
const dt_option = {
    "order": [[1, "desc"]],
    "lengthMenu": [10, 25, 50, 100],
    "pageLength": 10
};
let logInterval;

$(document).ready(function () {
    getSummary();

    $('#upload-task-table').DataTable(dt_option);

    $("table#upload-task-table").on('click', '.show-log', function (e) {
        $('#log-modal').css('display', 'block');

        const taskID = $(e.target).parent().parent().parent().children(0).children(0).html().trim();
        updateTargetLog(taskID);
        logInterval = setInterval(function () {
            updateTargetLog(taskID);
        }, 5000);
    });

    $(".close").on('click', function () {
        clearInterval(logInterval);
    });

});

window.onclick = function (event) {
    if (event.target === modal) {
        modal.css('display', 'none');
    }
};

function updateTargetLog(taskID) {
    $.ajax({
        url: "/api/preprocess/task/" + taskID,
        dataType: "json",
        type: 'GET',
        context: document.body,
        success: function (data) {
            const logContent = $("#log-body");
            logContent.empty();
            logContent.html(data.log);
        }
    });
}

function submitform() {
    const form = $("#upload_form");
    const formData = new FormData(form[0]);
    $("#file-submit").addClass('disabled');
    $.ajax({
        type: "POST",
        url: "/api/preprocess/task/",
        data: formData,
        enctype: 'multipart/form-data',
        processData: false,
        contentType: false,
        cache: false,
        success: function (data) {
            location.reload();
        },
        error: function (data) {
            $("#message").html(data.responseText);
            $("#file-submit").removeClass('disabled');
        },

    });
}


function getSummary() {

    $.ajax({
        type: "GET",
        url: "/api/preprocess/summary/",
        success: function (data) {
            let total_claims = data.cw_count + data.non_cw_count;
            let preClaim = parseInt(document.getElementById("claim-data").innerHTML);

            $("#claim-data").html(total_claims);
            $("#cw-data").html(data.cw_count);
            $("#no-cw-data").html(data.non_cw_count);
            $("#emp-data").html(data.emp_count);
            let data_list = [];
            data_list.push(data.cw_count);
            data_list.push(data.non_cw_count);
            if (preClaim !== total_claims) {
                drawPieChart(data_list)
            }

        },
        error: function (data) {
        },
    });
}

function drawPieChart(data_list) {
    let ctx = $("#claim-chart");
    const sum = data_list[0] + data_list[1];
    let percent_data = [Math.round(data_list[0] / sum * 10000) / 100, Math.round(data_list[1] / sum * 10000) / 100];
    let table_data = {
        datasets: [{
            data: percent_data
        }],
        // These labels appear in the legend and in the tooltips when hovering different arcs
        labels: [
            'Commonwealth',
            'All Industries'
        ]
    };
    const claimChart = new Chart(ctx, {
        type: 'pie',
        data: table_data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
        }
    });
}


function deleteform(id) {
    const choice = confirm("This will delete both the preprocess task and uploaded data from database. Are you sure?");
    if (choice) {
        $.ajax({
            type: "DELETE",
            url: "/api/preprocess/task/" + id,
            headers: {
                "X-CSRFToken": $("input[name=csrfmiddlewaretoken]").val()
            },
            success: function (data) {
                location.reload();
            },
            error: function (data) {
                $("#message").html(data.responseText)
            },
        });
    }

}

function getTaskStatus() {
    $.ajax({
        url: "/api/preprocess/task/",
        dataType: "json",
        type: 'GET',
        context: document.body,
        success: function (data) {
            $.each(data, function (k, v) {
                const domID = "status-" + v.file_name;
                console.log(domID);
                const status_dom = $("td[id='" + domID + "']");
                if (status_dom.html() !== undefined) {
                    status_dom.html(v.status);
                    getSummary();
                }
            });
        }
    });
}

function init_charts(freq_map) {
  var data_arr = new Array();
  var chartDom = document.getElementById("offwork_gap_pie_chart");
  var myChart = echarts.init(chartDom);
  var option;

  for (const [key, value] of Object.entries(freq_map)) {
    var map = {}
    map["name"] = key;
    map["value"] = value; 
    data_arr.push(map);
  }

  option = {
    title: {
      text: 'Predicted nature code distribution',
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
        data: data_arr
      }
    ]
  };

  myChart.setOption(option);
  
}



function submitNeuralForm() {
    const form = $("#upload_neural_form");
    const formData = new FormData(form[0]);
    $("#neural-file-submit").addClass('disabled');
    $.ajax({
        type: "POST",
        url: "/api/neural/task/",
        data: formData,
        enctype: 'multipart/form-data',
        processData: false,
        contentType: false,
        cache: false,
        success: function (data) {
            $(function() {
                init_charts(data["freq_map"]);

                // Get the child element node
                var disable = document.getElementsByClassName("dataTables_empty");
                // Remove the child element from the document
                for (item of disable) {
                    item.parentNode.removeChild(item);
                }
                $.each(data["prediction"], function(i, arr) {
                    var $tr = $('<tr>').append(
                        $('<td>').text(arr[19]),
                        $('<td>').text(arr[0]),
                        $('<td>').text(arr[1]),
                        $('<td>').text(arr[3]),
                        $('<td>').text(arr[7]),
                        $('<td>').text(arr[8]),
                        $('<td>').text(arr[9]),
                        $('<td>').text(arr[10]),
                        $('<td>').text(arr[15]),
                        $('<td>').text(arr[16]),
                        $('<td>').text(arr[17]),
                    ).appendTo('#neural_tbody');
                });
            });
        },
        error: function (data) {
            $("#message").html(data.responseText);
            $("#neural-file-submit").removeClass('disabled');
        },

    });
}

window.setInterval(getTaskStatus, 5000);