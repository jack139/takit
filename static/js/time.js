/*************************************************
 * Class Time 
 * @author chenxiangzhen
 * @created 2011-04-06
 * @version v1.0
 * @function 工具类，时间相关信息
 *************************************************/
function Time()
{
	var tCurrentTime = new Date();
	this.m_iYear = tCurrentTime.getFullYear();
	this.m_iMonth = tCurrentTime.getMonth()+1;
	this.m_iDay = tCurrentTime.getDate();
	this.m_iHour = tCurrentTime.getHours();
	this.m_iMinute = tCurrentTime.getMinutes();
	this.m_iSecond = tCurrentTime.getSeconds();
	this.m_iMilliseconds = tCurrentTime.getTime();//返回 1970 年 1 月 1 日至今的毫秒数
}
/*************************************************
Function:		setTimeByMis
Description:	设置时间
Input:			iMilliseconds: 1970 年 1 月 1 日至今的毫秒数
Output:			无
return:			无
*************************************************/
Time.prototype.setTimeByMis = function(iMilliseconds)
{
	var tSetTime = new Date(iMilliseconds);
	this.m_iYear = tSetTime.getFullYear();
	this.m_iMonth = tSetTime.getMonth()+1;
	this.m_iDay = tSetTime.getDate();
	this.m_iHour = tSetTime.getHours();
	this.m_iMinute = tSetTime.getMinutes();
	this.m_iSecond = tSetTime.getSeconds();
	this.m_iMilliseconds = iMilliseconds;
}
/*************************************************
Function:		getStringTime
Description:	获取时间字符串
Input:			无
Output:			无
return:			string  yyyy-MM-dd HH:mm:ss
*************************************************/
Time.prototype.getStringTime = function()
{
	var szYear = "" + this.m_iYear;
	
	var szMonth;
	if(this.m_iMonth < 10)
	{
		szMonth = "0" + this.m_iMonth;
	}
	else
	{
		szMonth = "" + this.m_iMonth;
	}
	
	var szDay;
	if(this.m_iDay < 10)
	{
		szDay = "0" + this.m_iDay;
	}
	else
	{
		szDay = "" + this.m_iDay;
	}
	
	var szHour;
	if(this.m_iHour < 10)
	{
		szHour = "0" + this.m_iHour;
	}
	else
	{
		szHour = "" + this.m_iHour;
	}
	
	var szMinute;
	if(this.m_iMinute < 10)
	{
		szMinute = "0" + this.m_iMinute;
	}
	else
	{
		szMinute = "" + this.m_iMinute;
	}
	
	var szSecond;
	if(this.m_iSecond < 10)
	{
		szSecond = "0" + this.m_iSecond;
	}
	else
	{
		szSecond = "" + this.m_iSecond;
	}
	var szCurrentTime = szYear + "-" + szMonth + "-" + szDay + " " + szHour + ":" + szMinute + ":" + szSecond;
	return szCurrentTime;
}
/*************************************************
Function:		parseTime
Description:	通过时间字符串设置时间
Input:			szTime 时间 yyyy-MM-dd HH:mm:ss
Output:			无
return:			无
*************************************************/
Time.prototype.parseTime = function(szTime)
{
	var aDate = szTime.split(' ')[0].split('-');
	var aTime = szTime.split(' ')[1].split(':');
	
	this.m_iYear = parseInt(aDate[0],10);
	this.m_iMonth = parseInt(aDate[1],10);
	this.m_iDay = parseInt(aDate[2],10);
	
	this.m_iHour = parseInt(aTime[0],10);
	this.m_iMinute = parseInt(aTime[1],10);
	this.m_iSecond = parseInt(aTime[2],10);
	
	var tTime = new Date();
	tTime.setFullYear(this.m_iYear);
	tTime.setMonth(this.m_iMonth - 1, this.m_iDay);
	
	tTime.setHours(this.m_iHour);
	tTime.setMinutes(this.m_iMinute);
	tTime.setSeconds(this.m_iSecond);
	
	this.m_iMilliseconds = tTime.getTime();
}
