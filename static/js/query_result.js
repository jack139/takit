var m_todo = null;
var m_dots = "..";
var m_result = null;

function doFirst(todo)
{
	m_todo=todo;
	showTips("查询中 "+m_dots);
	setTimeout(checkout, 500);
}

function showTips(strTips)
{
	$('#tips').html(strTips);
}

function appendTD2(tr, str){
	var td=$("<td class=\"dotbt\">" + str + "</td>");
	td.appendTo(tr);
}

function appendTD(tr, str){
	var td=$("<td class=\"dotb\">" + str + "</td>");
	td.appendTo(tr);
}

function createTable(filter)
{
	if (m_result==null) return;

	var table = $("<table>");
	var tr = $("<tr></tr>");

	$("#result").empty();
	tr.appendTo(table);
	appendTD2(tr, "序号");
	appendTD2(tr, "车次");
	appendTD2(tr, "出发站");
	appendTD2(tr, "到达站");
	appendTD2(tr, "出发日期");
	appendTD2(tr, "出发时间");
	appendTD2(tr, "到达时间");
	appendTD2(tr, "商务");
	appendTD2(tr, "特等");
	appendTD2(tr, "一等");
	appendTD2(tr, "二等");
	appendTD2(tr, "高软");
	appendTD2(tr, "软卧");
	appendTD2(tr, "硬卧");
	appendTD2(tr, "软座");
	appendTD2(tr, "硬座");
	appendTD2(tr, "无座");
	appendTD2(tr, "其他");
	appendTD2(tr, "备注");
	table.appendTo(($("#result")));
	$.each(m_result, function(i, item){
		var t_class = item[0]["station_train_code"][0];
		var add_to = false;
		switch(filter){
		case "all":
			add_to=true;
			break;
		case "GC":
			if (t_class=="G" || t_class=="C") add_to=true;
			break;
		case "D":
		case "Z":
		case "T":
		case "K":
			if (t_class==filter) add_to=true;
			break;
		case "others":
			if (t_class!="G" && t_class!="C" && t_class!="D" &&
			    t_class!="Z" && t_class!="T" && t_class!="K" ) 
				add_to=true;
			break;
		}
		if (add_to){
			tr = $("<tr></tr>")
			tr.appendTo(table);
			appendTD(tr, i+1);
			appendTD(tr, item[0]["station_train_code"]);
			appendTD(tr, item[0]["from_station_name"]);
			appendTD(tr, item[0]["to_station_name"]);
			appendTD(tr, item[0]["start_train_date"]);
			appendTD(tr, item[0]["start_time"]);
			appendTD(tr, item[0]["arrive_time"]);
			appendTD(tr, item[0]["swz_num"]);
			appendTD(tr, item[0]["tz_num"]);
			appendTD(tr, item[0]["zy_num"]);
			appendTD(tr, item[0]["ze_num"]);
			appendTD(tr, item[0]["gr_num"]);
			appendTD(tr, item[0]["rw_num"]);
			appendTD(tr, item[0]["yw_num"]);
			appendTD(tr, item[0]["rz_num"]);
			appendTD(tr, item[0]["yz_num"]);
			appendTD(tr, item[0]["wz_num"]);
			appendTD(tr, item[0]["qt_num"]);
			if (item[1]!="")
				appendTD(tr, "<a class=\"rdact\" href=\"/order?todo="+m_todo+"&s="+item[1]+"\">订票</a>");
			else
				appendTD(tr, "n/a");
		}
	});
	$("#result").append("</table>");
}

function checkout()
{
	$.ajax({
		type: "GET",
		url: "/checkout",
		async: true,
		timeout: 15000,
		data: {todo:m_todo},
		//beforeSend: function(xhr) {
		//	xhr.setRequestHeader("If-Modified-Since", "0");
		//},
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
				if (retJson["status"]=="FINISH"){
					showTips("查询到"+retJson["result"].length+"条结果，耗时"+retJson["elapse"]+"秒");
					m_result = retJson["result"];
					createTable("all");
					showTips(retJson["comment"]);
				}
				else if (retJson["status"]=="FAIL"){
					showTips("查询中出错。" + retJson["comment"]);
				}
				else if (jQuery.isEmptyObject(retJson)){
					showTips("未找到查询结果！");
				}
				else {
					m_dots += ".";
					showTips("查询中 "+m_dots);
					setTimeout(checkout, 1000);
				}
			}
			else
			{
				showTips("网络异常！("+xhr.status+")");
			}
		}
	});
}

