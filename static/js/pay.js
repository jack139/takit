function showTips(strTips)
{
	$('#tips').html(strTips);
}

function hide_show()
{
	$('#alipay').hide();
	$('#check_result').show();
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
					//$("#"+todo).remove();
					window.location.href='\query';
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
