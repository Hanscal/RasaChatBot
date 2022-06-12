/**
 * Returns the current datetime for the message creation.
 */
function getCurrentTimestamp() {
	return new Date();
}

/**
 * Renders a message on the chat screen based on the given arguments.
 * This is called from the `showUserMessage` and `showBotMessage`.
 */
function renderMessageToScreen(args) {
	// local variables
	let displayDate = (args.time || getCurrentTimestamp()).toLocaleString('en-IN', {
		month: 'short',
		day: 'numeric',
		hour: 'numeric',
		minute: 'numeric',
	});
	let messagesContainer = $('.messages');

	// init element
	let message = $(`
	<li class="message ${args.message_side}">
		<div class="avatar"></div>
		<div class="text_wrapper">
			<div class="text">${args.text}</div>
			<div class="timestamp">${displayDate}</div>
		</div>
	</li>
	`);

	// add to parent
	messagesContainer.append(message);

	// animations
	setTimeout(function () {
		message.addClass('appeared');
	}, 0);
	messagesContainer.animate({ scrollTop: messagesContainer.prop('scrollHeight') }, 300);
}

/**
 * Displays the user message on the chat screen. This is the right side message.
 */
function showUserMessage(message, datetime) {
	renderMessageToScreen({
		text: message,
		time: datetime,
		message_side: 'right',
	});
}

/**
 * Displays the chatbot message on the chat screen. This is the left side message.
 */
function showBotMessage(message, datetime) {
	renderMessageToScreen({
		text: message,
		time: datetime,
		message_side: 'left',
	});
}

/**
 * Get input from user and show it on screen on button click.
 */
$('#send_button').on('click', function (e) {
	// get and show message and reset input
	console.log($('#msg_input').val())
	showUserMessage($('#msg_input').val());
	// $('#msg_input').val('');
	// 限制返回时间3000ms
	// setTimeout(function () {
	// 	showBotMessage(getResponse($('#msg_input').val()));
	// }, 3000);
	showBotMessage(getResponse($('#msg_input').val()))
	// 每次返回数据后清空文本框
	$('#msg_input').val('');
});

/**
 * Returns a random string. Just to specify bot message to the user.
 */
function randomstring(length = 20) {
	let output = '';

	// magic function
	var randomchar = function () {
		var n = Math.floor(Math.random() * 62);
		if (n < 10) return n;
		if (n < 36) return String.fromCharCode(n + 55);
		return String.fromCharCode(n + 61);
	};

	while (output.length < length) output += randomchar();
	return output;
}


function getResponse(input_message) {
	let result = ''
	$.ajax({
		type:'post',
		// ajax 默认为异步请求，如果需要同步返回，需要将async改成false
		async: false,
		url:'/live_assistant_ui',
		data: {"question":input_message},
		dataType: 'json',
		success: function (data) {
			// console.log(data.answer)
			result = data.answer
		}
	});
	return result

}

/**
 * Set initial bot message to the screen for the user.
 */
$(window).on('load', function () {
	showBotMessage('你好! 我是您的智能助手。');
});