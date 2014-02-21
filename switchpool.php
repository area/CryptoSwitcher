<?php
#
# Sample Socket I/O to CGMiner API
#
function getsock($addr, $port)
{
 $socket = null;
 $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
 if ($socket === false || $socket === null)
 {
	$error = socket_strerror(socket_last_error());
	$msg = "socket create(TCP) failed";
	echo "ERR: $msg '$error'\n";
	return null;
 }

 $res = socket_connect($socket, $addr, $port);
 if ($res === false)
 {
	$error = socket_strerror(socket_last_error());
	$msg = "socket connect($addr,$port) failed";
	echo "ERR: $msg '$error'\n";
	socket_close($socket);
	return null;
 }
 return $socket;
}
#
# Slow ...
function readsockline($socket)
{
 $line = '';
 while (true)
 {
	$byte = socket_read($socket, 1);
	if ($byte === false || $byte === '')
		break;
	if ($byte === "\0")
		break;
	$line .= $byte;
 }
 return $line;
}
#
function request($host, $port, $cmd)
{
 $socket = getsock($host, $port);
 if ($socket != null)
 {
	socket_write($socket, $cmd, strlen($cmd));
	$line = readsockline($socket);
	socket_close($socket);

	if (strlen($line) == 0)
	{
		echo "WARN: '$cmd' returned nothing\n";
		return $line;
	}

#	print "$cmd returned '$line'\n";

	if (substr($line,0,1) == '{')
		return json_decode($line, true);

	$data = array();

	$objs = explode('|', $line);
	foreach ($objs as $obj)
	{
		if (strlen($obj) > 0)
		{
			$items = explode(',', $obj);
			$item = $items[0];
			$id = explode('=', $items[0], 2);
			if (count($id) == 1 or !ctype_digit($id[1]))
				$name = $id[0];
			else
				$name = $id[0].$id[1];

			if (strlen($name) == 0)
				$name = 'null';

			if (isset($data[$name]))
			{
				$num = 1;
				while (isset($data[$name.$num]))
					$num++;
				$name .= $num;
			}

			$counter = 0;
			foreach ($items as $item)
			{
				$id = explode('=', $item, 2);
				if (count($id) == 2)
					$data[$name][$id[0]] = $id[1];
				else
					$data[$name][$counter] = $id[0];

				$counter++;
			}
		}
	}

	return $data;
 }

 return null;
}

if ($argv[5]=="")
  $host="127.0.0.1";
else
  $host=$argv[5];
if ($argv[6]=="")
  $port=4028;
else
  $port=$argv[6];
request($host, $port, "addpool|".$argv[1].",".$argv[2].",".$argv[3]);
if ($argv[4]=="clear")
{
  $found=0;
  while (!$found)
  {
    $pools=request($host, $port, "pools");
    foreach ($pools as $pool)
      if (array_key_exists("URL", $pool) && !$found)
        if ($pool["URL"]==$argv[1] && !$found)
        {
          request($host, $port, "switchpool|".$pool["POOL"]);
          $found=1;
        }
  }
  sleep(2);
  $pools=request($host, $port, "pools");
  $found=0;
  foreach ($pools as $pool)
    if (array_key_exists("URL", $pool))
    {
      if ($pool["URL"]==$argv[1] && !$found)
        $found=1;
      else
        $remove[$pool["POOL"]]=$pool["POOL"];
    }
  krsort($remove);
  foreach ($remove as $poolnum)
  {
    request($host, $port, "disablepool|".$poolnum);
    request($host, $port, "removepool|".$poolnum);
  }
}
?>
