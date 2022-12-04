const shortDate = {year: 'numeric', month: 'numeric', day: 'numeric'};
const longDate = {year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: "numeric"};
const modal = $('#log-modal');
const dt_option = {
    "order": [[0, "desc"]],
    "lengthMenu": [10, 25, 50, 100],
    "pageLength": 10,
};
let logInterval;

$(document).ready(function () {
    $('#predict-task-table').DataTable(dt_option);
    $(function () {
        $.datepicker.setDefaults({
            changeYear: true,
            changeMonth: true,
            dateFormat: 'yy-mm-dd'
        });
        $("#start_date").datepicker();
        $("#end_date").datepicker();
    });
    $(function () {
        $('#county_selector').selectpicker();
        $('#naics_codes').selectpicker();
    });
    $("table#predict-task-table").on('click', '.show-log', function (e) {
        $('#log-modal').css('display', 'block');
        const taskID = $(e.target).parent().parent().children('.task-id').html().trim();
        updateTargetLog(taskID);
        logInterval = setInterval(function () {
            updateTargetLog(taskID);
        }, 5000);
    });

    $(".close").on('click', function () {
        clearInterval(logInterval);
    });

    $('.note').tooltip({
        classes: {
            "ui-tooltip": "ui-corner-all"
        },
    });
});

window.onclick = function (event) {
    if (event.target === modal) {
        modal.css('display', 'none');
    }
};

function updateTargetLog(taskID) {
    $.ajax({
        url: "/api/prediction/task/" + taskID,
        dataType: "json",
        type: 'GET',
        context: document.body,
        success: function (data) {
            const logContent = $("#log-body");
            logContent.empty();
            let percentage = (parseFloat(data.progress) | 0).toString();
            logContent.html(data.log + `<br><br> <label>Prediction progress:</label> <progress value=\"${percentage}\" max=\"100\"> ${percentage}% </progress>` + percentage + '%');
        }
    });
}

function getTaskList() {
    $.ajax({
        url: "/api/prediction/task/",
        dataType: "json",
        type: 'GET',
        context: document.body,
        success: function (data) {
            $.each(data, function (k, v) {
                const status_dom = $("#status-" + v.id);
                const evaluation_dom = $("#evaluation-" + v.id);
                if (v.status != undefined) {
                    status_dom.html(v.status);
                    if (v.status == "Successful") {
                        let evaluation_div = document.createElement("div")
                        let evaluation_file_a;
                        let file_link = "evaluation/"+v.id.toString();
                        evaluation_file_a = '<a class="button" href=' + file_link + ' role="button">Evaluation</a>';
                        evaluation_div.innerHTML = evaluation_file_a;

                        evaluation_dom.html(evaluation_div);
                    }
                }
            });
        }
    });
}

function submitform() {
    var naics_values = $('#naics_codes').val();
    var county_values = $('#county_selector').val();
    var model_type = $('#model_type').val();
    $("#naics").val(naics_values.join(";"));
    $("#county").val(county_values.join(";"));
    $("#model").val(model_type);
    
    if ($("#naics").val()=="") {
        alert("Please select at least 1 NAICS code.");
    }
    else if ($("#county").val()=="") {
        alert("Please select at least 1 county.");
    }
    else if ($("#model").val()=="") {
        alert("Please select a model.");
    } 
    else if ($("#severity").val()=="") {
        alert("Please select a severity.");
    }
    else {
        const form = $("#predict_form");
        $.ajax({
            type: "POST",
            url: "/api/prediction/task/",
            data: form.serialize(),
            success: function (data) {
                location.reload();
            },
            error: function (data) {
                $("#message").html(data.responseText);
            },

        });
    }
}

function deleteform(id) {

    const choice = confirm("This will delete both the prediction task and prediction output. Are you sure?");
    if (choice) {
        $.ajax({
            type: "DELETE",
            url: "/api/prediction/task/" + id,
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

function naics_level_selected() {
    var level = document.getElementById("naics_level").value;
    var select = document.getElementById('naics_codes');
    select.innerHtml = "";

    if (level) {
        $("#naics_codes").find('option').remove();
        var records = naics_data[level];
        for (i=0;i<records.length;i++) {
            option = document.createElement( "option" );
            option.value = records[i][0];
            option.text = records[i][0] +" - " + records[i][1];
            select.add(option);
        }
        document.getElementById('naics_code_row').hidden = false;
        $("#naics_codes").val('default').selectpicker('refresh');
    }
    
}
window.setInterval(getTaskList, 5000);
