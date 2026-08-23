use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello {}, welcome to HermesSwarm!", name)
}

#[tauri::command]
async fn execute_workflow(workflow_json: String) -> Result<String, String> {
    // 调用Python sidecar执行工作流
    // TODO: 启动Python子进程，通过stdin/stdout通信
    Ok(format!("Workflow executed: {}", workflow_json))
}

#[tauri::command]
async fn start_python_backend() -> Result<String, String> {
    // 启动Python后端服务
    // TODO: 启动uvicorn服务，返回端口
    Ok("Python backend started on port 8765".to_string())
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            greet,
            execute_workflow,
            start_python_backend
        ])
        .setup(|_app| {
            #[cfg(debug_assertions)]
            {
                let window = _app.get_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}