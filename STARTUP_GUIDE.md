# Grant Research Agent Startup Guide

Use this each day to start the UI on your machine.

## 1) Open PowerShell
Open Windows PowerShell or Terminal in the project folder.

```powershell
cd "F:\Grant Research Agent 3.0"
```

## 2) Allow local script execution if needed
If PowerShell blocks scripts, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## 3) Start the app
Run:

```powershell
.\start.ps1
```

This will:
- create a virtual environment if needed
- install the requirements
- launch the app on port 8080

## 4) Open the UI in a browser
Use one of the following URLs:

- Local machine: http://localhost:8080/
- Other users on your network: http://<your-lan-ip>:8080/

Example:

```text
http://10.0.1.25:8080/
```

## 5) Optional: open the firewall for other users
If you want other users on your network to access the app, run PowerShell as Administrator and allow inbound traffic on port 8080:

```powershell
netsh advfirewall firewall add rule name="GrantAgent8080" dir=in action=allow protocol=TCP localport=8080
```

## 6) Stop the app when finished
In the terminal running the app, press:

```text
Ctrl + C
```

## 7) Restart later
Repeat steps 1-4.

## Notes
- The app listens on port `8080`.
- The default UI is the home page at `/`.
- Share links are in the format:

```text
http://<your-lan-ip>:8080/share/<uid>
```

Example:

```text
http://10.0.1.25:8080/share/b5bab4f0b5a042fba342a290a7fd9445
```
