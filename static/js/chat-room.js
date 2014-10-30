(function() {
    var send_message = function () {
        var input = $("textarea#say");
        var msg = input.val();
        var data = {};
        data.message = msg;
        $.post("/chat/say", data, function(data, status){
            var success = false;
            var rsp = null;
            if(status=="success"){
                rsp = JSON.parse(data);
                if(rsp.success) success = true;
            }else{
                add_message("系统", get_now_time_string(), '<p class="text-danger">' + "发送失败: " + status + '</p>');
            }
            if(success){
                input.val("");
            }else{
                add_message("系统", get_now_time_string(), '<p class="text-danger">' + "发送失败: " + rsp.message + '</p>');
            }
        });
    };
    var add_message = function (name, time, msg) {
        var table_head = $("#chat-sample");
        var sample = table_head.clone();
        var text_id = "chat-log-" + last_message_index;
        sample.attr("id", text_id);
        var header = sample.children("#chat-header");
        header.empty();
        header.append($("<strong>" + name + "</strong>"));
        header.append($("<br>"));
        header.append($("<small>" + time + "</small>"));
        var content = sample.children("#chat-content");
        content.empty();
        content.append($("<p>" + msg + "</p>"));
        sample.hide();
        //table_head.after(sample);
        $("#chat-logs").append(sample);
        sample.fadeIn("slow");
        $("body").animate({scrollTop: sample.offset().top}, 300);
    };
    var join_room = function () {
        $.getJSON("/chat/update?method=join", function (result) {
            for (var i = 0; i < result.message.length; i++) {
                var pair = result.message[i];
                add_message(pair.name, pair.time, pair.message);
                last_message_index = pair.index;
            }
        });
    };
    var last_message_index = "";
    var listen_room = function () {
        $.getJSON("chat/update?method=listen&index=" + last_message_index, function (result) {
            is_reconnection = false;
            for (var i = 0; i < result.message.length; i++) {
                var pair = result.message[i];
                add_message(pair.name, pair.time, pair.message);
                last_message_index = pair.index;
            }
            listen_room();
        });
    };
    var get_now_time_string = function() {
      return (new Date()).toISOString().replace("T", " ").replace("Z", "").substr(0, 19);
    };
    var is_reconnection = false;
    var reconnection_delay = 3;
    var on_connection_error = function(respones, error) {
        if(this.url.substr(0, 25) == "chat/update?method=listen"){
            //add_message("系统", get_now_time_string(), '<p class="text-danger">' + "通讯错误, " + reconnection_delay + "s后尝试重新连接" + '</p>');
            is_reconnection = true;
            setTimeout(function(){
                //add_message("系统", get_now_time_string(), '<p class="text-info">' + "尝试重新连接中..." + '</p>');
                listen_room();
/*                setTimeout(function(){
                    if(is_reconnection)
                        add_message("系统", get_now_time_string(), '<p class="text-success">' + "重新连接成功" + '</p>');
                }, 1000);*/
            }, reconnection_delay * 1000);
        }
    };
    $().ready(function () {
        $.ajaxSetup({error: on_connection_error});
        $("button#btn-say").click(send_message);
        $("textarea#say").keypress(function(event){
            var checkbox_enter = $("input#checkbox-enter");
            if(event.which == 10 && checkbox_enter.prop("checked")) send_message();
            if(event.which == 13 && !checkbox_enter.prop("checked")) send_message();
        });

        join_room();
        listen_room();
    });
})();