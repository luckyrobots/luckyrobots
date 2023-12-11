if (Get-Command nodemon -ErrorAction SilentlyContinue) {
    # If the executable exists, echo 1
    echo starting server with nodemon:
    nodemon -w .\Resources\SignallingWebServer --exec "powershell -File" .\Resources\SignallingWebServer\platform_scripts\cmd\Start_SignallingServer.ps1
} else {
    # If the executable does not exist, echo 2
    echo nodemon is not found in your system, please install it with npm install -g nodemon
    echo starting server with node: (it will not restart automatically if you change the code, or a crash happens)
    node .\Resources\SignallingWebServer\platform_scripts\cmd\Start_SignallingServer.ps1 
}
