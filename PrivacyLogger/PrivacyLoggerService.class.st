Class {
	#name : #PrivacyLoggerService,
	#superclass : #Object,
	#instVars : [
		'server',
		'logFile',
		'recent'
	],
	#category : #PrivacyLogger
}

{ #category : #server }
PrivacyLoggerService >> handleIndex [

	| tmp1 tmp3 |
	tmp1 := '<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Percepta Debug Monitor</title>
<style>
body { background:#0B0D12; color:#EAEAF0; font-family:sans-serif; margin:20px; }
h2 { color:#7AA7FF; }
#log { margin-top:20px; font-family:monospace; }
.row { padding:6px; border-bottom:1px solid #222; }
.bad { color:#FF6B6B; }
.ok { color:#4ADE80; }
</style>
</head>
<body>
<h2>Percepta Live Debug Log</h2>
<div id="status">Connecting...</div>
<div id="log"></div>

<script>
async function tick(){
  try{
    const r = await fetch("/recent");
    const data = await r.json();
    document.getElementById("status").textContent =
      "Connected • Events: " + data.length;

    const log = document.getElementById("log");
    let html = "";
    for(let i=data.length-1;i>=0;i--){
      const e = data[i];
      const cls = e.event === "detection" ? "bad" : "ok";
      html += "<div class=row><span class="+cls+">"
        + (e.time_local || "") + " — "
        + (e.message || JSON.stringify(e))
        + "</span></div>";
    }
    log.innerHTML = html;
  }catch(e){
    document.getElementById("status").textContent = "Disconnected";
  }
  setTimeout(tick, 500);
}
tick();
</script>
</body>
</html>'.
	tmp3 := ZnResponse new.
	tmp3
		statusLine: (ZnStatusLine code: 200);
		entity: (ZnEntity with: tmp1 type: ZnMimeType textHtml).
	^ tmp3 yourself
]

{ #category : #server }
PrivacyLoggerService >> handleLogPost: arg1 [

	| tmp1 tmp3 tmp8 |
	tmp1 := arg1 entity contents.
	[ tmp3 := NeoJSONReader fromString: tmp1 ]
		on: Error
		do: [ :arg2 |
			| tmp5 |
			tmp5 := Dictionary new.
			tmp5
				at: 'ok' put: false;
				at: 'error' put: 'Invalid JSON'.
			^ self jsonResponse: 400 object: tmp5 yourself ].
	self rememberEvent: tmp3.
	[
	| tmp6 |
	logFile ifNil: [
		logFile := FileLocator documents / 'privacy-audit.jsonl' ].
	tmp6 := NeoJSONWriter toString: tmp3.
	logFile
		ensureCreateFile;
		writeStreamDo: [ :arg3 |
			arg3
				setToEnd;
				nextPutAll: tmp6;
				cr;
				flush ] ]
		on: Error
		do: [ :arg4 |
			Transcript
				show: 'Log file write failed: ';
				show: arg4 messageText;
				cr ].
	tmp8 := Dictionary new.
	tmp8 at: 'ok' put: true.
	^ self jsonResponse: 200 object: tmp8 yourself
]

{ #category : #server }
PrivacyLoggerService >> handleRecentGet [

	^ self jsonResponse: 200 object: recent asArray
]

{ #category : #public }
PrivacyLoggerService >> handleRequest: arg1 [

	| tmp1 |
	tmp1 := arg1 uri path.
	(tmp1 isEmpty and: [ arg1 method = #GET ]) ifTrue: [
		^ self handleIndex ].
	(tmp1 = 'recent' and: [ arg1 method = #GET ]) ifTrue: [
		^ self handleRecentGet ].
	(tmp1 = 'log' and: [ arg1 method = #POST ]) ifTrue: [
		^ self handleLogPost: arg1 ].
	^ ZnResponse notFound: tmp1
]

{ #category : #server }
PrivacyLoggerService >> jsonResponse: arg1 object: arg2 [

	| tmp1 tmp3 |
	tmp1 := NeoJSONWriter toString: arg2.
	tmp3 := ZnResponse new.
	tmp3
		statusLine: (ZnStatusLine code: arg1);
		entity: (ZnEntity with: tmp1 type: ZnMimeType applicationJson).
	^ tmp3 yourself
]

{ #category : #server }
PrivacyLoggerService >> rememberEvent: arg1 [

	recent ifNil: [ recent := OrderedCollection new ].
	recent addLast: arg1.
	recent size > 300 ifTrue: [ recent removeFirst ]
]

{ #category : #server }
PrivacyLoggerService >> startOn: arg1 [

	logFile := FileLocator documents / 'privacy-audit.jsonl'.
	recent := OrderedCollection new.
	server := ZnServer startOn: arg1.
	server
		bindingAddress: (NetNameResolver addressFromString: '127.0.0.1');
		delegate: self.
	Transcript
		show:
			'PrivacyLoggerService started on http://127.0.0.1:' , arg1 asString
			, '/';
		cr
]

{ #category : #accessing }
PrivacyLoggerService >> stop [

	server ifNotNil: [
		server stop.
		server := nil ].
	Transcript
		show: 'PrivacyLoggerService stopped';
		cr
]
