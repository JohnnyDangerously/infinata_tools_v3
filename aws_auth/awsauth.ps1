# To run this file you will need to open Powershell as administrator and first run:
# Set-ExecutionPolicy Unrestricted
# Then source this script by running:
# . .\awsauth.ps1

$save_dir=Resolve-Path ~/Downloads
$project_dir = "C:\Projects"
$virtualenv_dir = $project_dir + "\virtualenvs"

$client = New-Object System.Net.WebClient

function InstallPythonMSI($installer) {
	$Arguments = @()
	$Arguments += "/i"
	$Arguments += "`"$installer`""
	$Arguments += "ALLUSERS=`"1`""
	$Arguments += "/passive"

	Start-Process "msiexec.exe" -ArgumentList $Arguments -Wait
}

function download_file([string]$url, [string]$d) {
	# Downloads a file if it doesn't already exist
	if(!(Test-Path $d -pathType leaf)) {
		# get the file
		write-host "Downloading $url to $d";
		$client.DownloadFile($url, $d);
	}
}

function get-python-ver($version) {
	# Download Python indicated by version. For example:
	#  > get-python-ver 3.4.0rc1
	# or
	#  > get-python-ver 2.7.6

	$filename = 'python-' + $version + '.amd64.msi';
	$save_path = '' + $save_dir + '\' + $filename;
	if(!(Test-Path -pathType container $save_dir)) {
		write-host -fore red $save_dir " does not exist";
		exit;
	}

	$url = 'http://www.python.org/ftp/python/' + $version.Substring(0,5) + '/' + $filename;
	download-file $url $save_path
	write-host "Installing Python"
	InstallPythonMSI $save_path $target_dir

	write-host "Add Python to the PATH"
	[Environment]::SetEnvironmentVariable("Path", "$env:Path;C:\Python27\;C:\Python27\Scripts\", "User")
}