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
			case "PAY":
			case "SCAN":
				if (exist!="wait_pay") remove=true;
				break;
			}
			if (remove)
				$("#"+item["id"]).remove();
			else
				return;
		}

		switch(item["status"]){
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
		}

	});
}

function checkout()
{
	$.ajax({
		type: "GET",
		url: "/checkout_sjrand3",
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

