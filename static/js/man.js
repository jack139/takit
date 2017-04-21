var m_dots = "..";
var id_list = null;
var status_list = null;
var rand_num = 4;

function doFirst(num)
{
	rand_num = num;
	showTips("查询事件 "+m_dots);
	setTimeout(checkout, 500);
}

function showTips(strTips)
{
	$('#tips').html(strTips);
}

function checkSjrand(todo)
{
	var rand_code = $("#sj_"+todo)[0]["value"];

	$.ajax({
		type: "GET",
		url: "/verify_sjrand",
		async: true,
		timeout: 15000,
		data: {todo:todo, rand_code:rand_code},
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
				if (retJson["ret"]==0){
					showTips("已提交验证");
					$("#"+todo).remove();
				}
				else
					showTips("提交失败，可能其他人已处理");
					$("#"+todo).remove();
			}
			else
			{
				showTips("网络异常！("+xhr.status+")");
			}
		}
	});
}

function payOK(todo, success)
{
	$.ajax({
		type: "GET",
		url: "/pay_result",
		async: true,
		timeout: 15000,
		data: {todo:todo, success:success},
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
				if (retJson["ret"]==0){
					showTips("已提交");
					$("#"+todo).remove();
				}
				else
					showTips("提交失败");
			}
			else
			{
				showTips("网络异常！("+xhr.status+")");
			}
		}
	});
}

function flashID(list)
{
	var new_list=[], new_status={};

	$.each(list, function(i, item){new_list[i]=item["id"]; new_status[item["id"]]=item["status"]});
	if (id_list!=null){ 
		$.each(id_list, function(i, item){
			if (new_list.indexOf(item)==-1)
				$("#"+item).remove();
			else if (status_list[item]!=new_status[item])
				$("#"+item).remove();
		});
	}
	id_list=new_list;
	status_list=new_status;
}

function createImage(list)
{
	$.each(list, function(i, item){
		if ($("#"+item["id"]).length>0){
			var remove=false;
			exist = $("#"+item["id"]).parent()[0]['id']
			switch(item["status"]){
			case "SJRAND":
			case "SJRAND_P":
				if (exist.substring(0,11)!="wait_sjrand") remove=true;
				break;
			case "PAY":
			case "SCAN":
				if (exist!="wait_pay") remove=true;
				break;
			default:
				if (item["man"]==1){
					if (exist!="wait_status") remove=true;
				}
				else{
					if (exist!="wait_auto") remove=true;
				}
				break;
			}
			if (remove)
				$("#"+item["id"]).remove();
			else
				return;
		}

		var uri="sjrand_p";

		switch(item["status"]){
		case "SJRAND":
			uri="sjrand";
		case "SJRAND_P":
			var ii;
			for(ii=1;ii<=rand_num;ii++){
				rand_position = "#wait_sjrand_"+ii;
				if ($(rand_position).children().length==0)
					break;
			} 
			if (ii<=rand_num){
				var image = $("<div id=\""+item["id"]+"\">" +
					"<image id=\"sjimg_"+item["id"]+"\" src=\"\\"+uri+"?todo="+item["id"]+"&s="+Math.random()+"\">&nbsp;"  +
					"<input class=\"formbutton\" type=\"button\" onclick=\"$('#sj_"+item["id"]+"')[0].value='';\" value=\"重来\">&nbsp;" +
					"<input class=\"formtextinput3\" type=\"text\" id=\"sj_"+item["id"]+"\" style=\"width:100px;\" name=\"rand_code\" value=\"\" readonly=\"readonly\"/>&nbsp;" +
					"<input class=\"formbutton\" type=\"button\" value=\"验证\" style=\"width:100px;height:30px;\" onclick=\"checkSjrand('"+item["id"]+"')\"/></div>");
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
			}
			break;
		case "PAY":
			var image = $("<div id=\""+item["id"]+"\">" +
				"<a class='act' href='/pay2?todo="+item["id"]+"' target='_blank' onclick='$(\"#"+item["id"]+"\").remove();'>付款</a>&nbsp;" + item["ticketPay"] +
				"元,&nbsp;" + item["orderNo"] +"(" +item["user"] + "), 车票保留至 <b>" + item["limit"] + "</b>. " +
				"&nbsp;payStatus=" + item["payStatus"] + "&nbsp;" +
				"&nbsp;<a class='rdact' href='/view_event?todo="+item["id"]+"' target='_blank'>查看详情</a>" +
				(item["return"]!=0?"<申请退票>":"")+(item["orderType"]==1?"<联程>":"")+(item["urgent"]==1?"<<<紧急>>>":"")+"</div>");
			image.appendTo(($("#wait_pay")));
			break;
		case "SCAN":
			var image = $("<div id=\""+item["id"]+"\">" +
				"<a class='rdact' href='/ali_form?todo="+item["id"]+"' target='_blank' onclick='$(\"#"+item["id"]+"\").remove();'>等待支付宝付款中</a>&nbsp;" + item["ticketPay"] +
				"元,&nbsp;" + item["orderNo"] +"(" +item["user"] + "), 车票保留至 <b>" + item["limit"] + "</b>. " +
				"&nbsp;payStatus=" + item["payStatus"] + "&nbsp;" +
				"&nbsp;<a class='rdact' href='/view_event?todo="+item["id"]+"' target='_blank'>查看详情</a>" +
				"&nbsp;" + "&nbsp;</div>");
			image.appendTo(($("#wait_pay")));
			break;
		case "SCAN2":
			var image = $("<div id=\""+item["id"]+"\">" +
				"<input type=\"button\" value=\"付款成功\" onclick=\"payOK('"+item["id"]+"', 1)\"/>&nbsp;" +
				"<input type=\"button\" value=\"重新支付\" onclick=\"payOK('"+item["id"]+"', 0)\"/>" +
				item["ticketPay"] + "元，&nbsp;" + item["orderNo"] +"(" +item["user"] +
				")&nbsp;<a class='rdact' href='/view_event?todo="+item["id"]+"' target='_blank'>查看详情</a>" + 
				"&nbsp;等待 " + item["elapse"] +" 秒</div>");
			image.appendTo(($("#wait_pay")));
			break;			
		default:
			if (item["man"]==1){
				var image = $("<div id=\""+item["id"]+"\">" +
					"<a class='rdact' href='/view_event?todo="+item["id"]+"' target='_blank'>人工处理</a>" +
					"&nbsp;" + item['status'] + "&nbsp;-&nbsp;"  + item['comment'] + "</div>");
				image.appendTo(($("#wait_status")));
			} 
			else{
				var image = $("<div id=\""+item["id"]+"\">" +
					"<a class='rdact' href='/view_event?todo="+item["id"]+"' target='_blank'>查看详情</a>" +
					"&nbsp;" + item['status'] + "&nbsp;-&nbsp;"  + item['comment'] + "</div>");
				image.appendTo(($("#wait_auto")));
			}
			break;
		}

	});
}

function checkout()
{
	$.ajax({
		type: "GET",
		url: "/checkout_sjrand",
		async: true,
		timeout: 15000,
		data: {num:rand_num},
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
					showTips("查询到待处理的事件("+ retJson["num"]+'个)');
					flashID(retJson["data"]);
					createImage(retJson["data"]);
				}
				else if (retJson["num"]==0){
					flashID([]);
					m_dots += ".";
					if (m_dots.length>10) m_dots = ".";
					showTips("没有需处理的事件 "+m_dots);					
				}
				else if (jQuery.isEmptyObject(retJson)){
					showTips("未找到查询结果！");
				}
				else {
					m_dots += ".";
					if (m_dots.length>20) m_dots = ".";
					showTips("查询事件 "+m_dots);
				}
			}
			else
			{
				showTips("网络异常！("+xhr.status+")");
			}
		}
	});

	setTimeout(checkout, 2000);
}

