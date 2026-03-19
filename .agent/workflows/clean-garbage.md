---
description: Clean up useless logs, tmp directories, and cached rendering artifacts to free up space and maintain a solidified structure.
---

This workflow removes crash logs, empty or bloated temporary folders, and leftover debug artifacts from the root and video directories.

// turbo-all
1. Remove all root level `.log` files.
```powershell
Remove-Item -Path ".\*.log" -Force -ErrorAction SilentlyContinue
```

2. Remove `.tmp` folders recursively.
```powershell
Remove-Item -Path ".\.tmp" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path ".\video\.tmp" -Recurse -Force -ErrorAction SilentlyContinue
```

3. Output success message.
```powershell
Write-Host "✅ Cleanup Complete! Logs and .tmp folders have been purged."
```
