var m_dots = "..";
var rand_num = 4;
var rand_num_p = 2;
var todo_list = [];
var timeout_list = [];

function doFirst(num, num2)
{
	rand_num = num;
	rand_num_p = num2;
	showTips("查询事件 "+m_dots);
	for (var i=0; i<num; i++){
		todo_list[i]='';
		setTimeout("checkout("+i+")", 500);
	}
}

function showTips(strTips)
{
	$('#tips').html(strTips);
}

function createImage(x, list)
{
	$.each(list, function(i, item){
		if ($("#"+item["id"]).length>0){ // 图片已存在
			return;
		}
		
		todo_list[x] = item["id"];

		var uri="sjrand_p";

		switch(item["status"]){
		case "SJRAND":
			uri="sjrand";
		case "SJRAND_P":
			rand_position = "#wait_sjrand_"+x;

			var image = $("<div id=\""+item["id"]+"\">" +
				"<image id=\"sjimg_"+item["id"]+"\" src=\"\\"+uri+"?todo="+item["id"]+"&s="+Math.random()+"\">&nbsp;"  +
				"<input class=\"formbutton\" type=\"button\" onclick=\"$('#sj_"+item["id"]+"')[0].value='';\" value=\"重来\">&nbsp;" +
				"<input class=\"formtextinput3\" type=\"text\" id=\"sj_"+item["id"]+"\" style=\"width:100px;\" name=\"rand_code\" value=\"\" readonly=\"readonly\"/>&nbsp;" +
				"<input class=\"formbutton\" type=\"button\" value=\"验证\" style=\"width:100px;height:30px;\" onclick=\"checkout("+x+")\"/></div>");
			image.appendTo(($(rand_position)));

			$('#sj_'+item["id"])[0].value="";
			
			$('#sjimg_'+item["id"]).click(function(e) {
				var offset = $(this).offset();
				var x = e.pageX - offset.left;
				var y = e.pageY - offset.top - 30;
				var s = String(Math.round(x))+','+String(Math.round(y));
				if ($('#sj_'+item["id"])[0].value.trim()=='')
					$('#sj_'+item["id"])[0].value = s;
				else
					$('#sj_'+item["id"])[0].value += (','+s);
			});
			break;
		}

	});
}

function checkout(x)
{
	var rand_code = '';
	var p = x<rand_num_p?0:1;
	
	clearTimeout(timeout_list[x]);
	
	if (todo_list[x]!=''){
		rand_code = $("#sj_"+todo_list[x])[0]["value"];
		if (rand_code=='') // 未打码
			var todo = '';
		else
			var todo = todo_list[x];
		// 删除当前图片
		$("#"+todo_list[x]).remove();
		todo_list[x]='';
	}

	$.ajax({
		type: "GET",
		url: "/checkout_sjrand2",
		async: true,
		timeout: 15000,
		data: {todo:todo, rand_code:rand_code, p:p},
		dataType: "json",
		complete: function(xhr, textStatus)
		{
			if(xhr.status == 403)
			{
				showTips("网络异常！(403)");
			}
			else if(xhr.status==200)
			{
				var retJson = JSON.parse(xhr.responseText);
				
				if (retJson["num"]>0){
					showTips("查询到待处理的事件");
					createImage(x, retJson["data"]);
					timeout_list[x]=setTimeout("checkout("+x+")", 15000);
				}
				else if (retJson["num"]==0){
					m_dots += (""+x);
					if (m_dots.length>20) m_dots = ""+x;
					showTips(m_dots);
					timeout_list[x]=setTimeout("checkout("+x+")", 2000);
				}
				else{
					showTips("未找到查询结果！" + x);
					timeout_list[x]=setTimeout("checkout("+x+")", 2000);
				}
			}
			else
			{
				showTips("网络异常！("+xhr.status+")");
			}
		}
	});
}

