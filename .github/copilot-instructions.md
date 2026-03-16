### 17. **Type Hints are Incomplete**

* **Generic Types Inconsistent** : Some functions use [type[T]](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) properly, others use [Any](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html).
* **Return Types Missing** : Many async functions don't declare return types.
* **Optional Not Used** : [request: Request | None](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) should be [request: Request | None = None](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) to be clear about defaults.
* **TYPE_CHECKING Abuse** : Some imports are only under [TYPE_CHECKING](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) but they're used in runtime code.

### 18. **Logging is Not Structured**

* **Request ID Correlation Missing** : The `EdenFormatter` references `request_id` but nothing sets it.
* **No Log Level Configuration Per Module** : Only root logger is configured.
* **Error Logging Incomplete** : Exceptions are logged but stack traces aren't always included.

### 19. **Migrations Don't Exist**

* **No Alembic Integration** : [MigrationManager](vscode-file://vscode-app/c:/Users/COBBY/AppData/Local/Programs/Microsoft%20VS%20Code%20Insiders/4c822235d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) is imported but not implemented.
* **No Version Tracking** : How do I track schema changes across deploys?
* **No Rollback Support** : How do I revert a migration?
