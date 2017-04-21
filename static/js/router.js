var m_todo = null;
var m_dots = "..";

function doFirst(todo)
{
	m_todo=todo;
	showTips("请稍后 "+m_dots);
	setTimeout(checkout, 500);
}

function showTips(strTips)
{
	$('#tips').html(strTips);
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
					showTips("操作结束！" + retJson["comment"]);
				}
				else if (retJson["lock"]==0 && retJson["man"]==1){
					var time_txt = "耗时"+retJson["elapse"]+"秒";
					if (retJson["event"]=="ORDER_UI"){
						switch(retJson["status"]){
						case "SJRAND":
							window.location.href='/order2?todo='+m_todo;
							break;
						case "SJRAND_P":
							window.location.href='/verify?todo='+m_todo;
							break;
						case "PAY":
						case "SCAN2":
							window.location.href='/pay?todo='+m_todo;
							break;
						case "SCAN":
							window.location.href='/ali_form?todo='+m_todo;
							break;
						default:
							m_dots += ".";
							showTips("请稍后 "+m_dots+retJson["status"]);
							setTimeout(checkout, 1000);
						}
					}
					else{
						switch(retJson["status"]){
						case "SCAN":
							window.location.href='/ali_form?todo='+m_todo;
							break;
						default:
							m_dots += ".";
							showTips("请稍后 "+m_dots+retJson["status"]);
							setTimeout(checkout, 1000);
						}
					}
				}
				else if (jQuery.isEmptyObject(retJson)){
					showTips("未找到结果！");
				}
				else {
					m_dots += ".";
					showTips("请稍后 "+m_dots+retJson["comment"]);
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

