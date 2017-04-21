var m_todo = null;
var m_dots = "..";

function doFirst(todo)
{
	m_todo=todo;
	showTips("查询随机码 "+m_dots);
	setTimeout(checkout, 500);
}

function showTips(strTips)
{
	$('#tips').html(strTips);
}

function createImage()
{
	var image = $("<image id=\"sjimg\" src=\"\sjrand_p?todo="+ m_todo +"\">");

	//$("#sjrand").empty();
	image.appendTo(($("#sjrand")));
	$("#sjrand").append("</table>");

	//$('#sj_input')[0].value='';
	
	$('#sjimg').click(function(e) {
		var offset = $(this).offset();
		var x = e.pageX - offset.left;
		var y = e.pageY - offset.top - 30;
		var s = String(Math.round(x))+','+String(Math.round(y));
		if ($('#sj_input')[0].value.trim()=='')
			$('#sj_input')[0].value = s;
		else
			$('#sj_input')[0].value += (','+s);
	});

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
				if (retJson["status"]=="SJRAND_P"){
					showTips("查询到随机码("+ retJson["comment"]+') 耗时'+retJson["elapse"]+"秒");
					createImage();
				}
				else if (retJson["status"]=="FAIL"){
					showTips("查询随机码出错。" + retJson["comment"]);
				}
				else if (jQuery.isEmptyObject(retJson)){
					showTips("未找到查询结果！");
				}
				else {
					m_dots += ".";
					showTips("查询随机码 "+m_dots);
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

