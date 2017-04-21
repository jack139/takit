var m_todo = null;
var m_dots = "..";
var m_api_key = null;
var m_secret = null;

function doFirst(todo, api_key, secret)
{
	m_todo=todo;
	m_api_key=api_key;
	m_secret=secret;
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
		url: "/api/checkout",
		async: true,
		timeout: 15000,
		data: {todo:m_todo, api_key:m_api_key, secret:m_secret},
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
					switch(retJson["status"]){
					case "SCAN":
						window.location.href='/api/ali_form?todo='+m_todo
							+'&api_key='+m_api_key+'&secret='+m_secret;
						break;
					default:
						m_dots += ".";
						showTips("请稍后 "+m_dots+retJson["status"]);
						setTimeout(checkout, 1000);
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

