# Ver reglas que permiten conexiones desde 10.8.1.1
Get-NetFirewallRule | Get-NetFirewallAddressFilter | Where-Object { $_.RemoteAddress -like "*10.8.1.1*" } | Get-NetFirewallRule | Format-Table DisplayName, Enabled, Direction, @{Name='RemoteIP';Expression={$_.RemoteAddress}} -AutoSize

# Ver reglas que permiten conexiones desde 10.8.3.1
Get-NetFirewallRule | Get-NetFirewallAddressFilter | Where-Object { $_.RemoteAddress -like "*10.8.3.1*" } | Get-NetFirewallRule | Format-Table DisplayName, Enabled, Direction, @{Name='RemoteIP';Expression={$_.RemoteAddress}} -AutoSize

# Ver todas las reglas de Firebird
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*Firebird*" } | Format-Table DisplayName, Enabled, Direction -AutoSize

