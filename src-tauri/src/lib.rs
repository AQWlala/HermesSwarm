use std::collections::HashMap;
use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello {}, welcome to HermesSwarm!", name)
}

#[tauri::command]
async fn execute_workflow(workflow_json: String) -> Result<String, String> {
    Ok(format!("Workflow executed: {}", workflow_json))
}

#[tauri::command]
async fn start_python_backend() -> Result<String, String> {
    Ok("Python backend started on port 8765".to_string())
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            greet,
            execute_workflow,
            start_python_backend
        ])
        .setup(|app| {
            let mut env = HashMap::new();
            env.insert("PORT".to_string(), "8765".to_string());
            env.insert("HOST".to_string(), "127.0.0.1".to_string());

            let sidecar = tauri::api::process::Command::new_sidecar("hermesswarm-backend")
                .expect("Failed to find backend sidecar")
                .envs(env);

            let (mut rx, _child) = sidecar.spawn()
                .expect("Failed to spawn backend sidecar");

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        tauri::api::process::CommandEvent::Stdout(line) => {
                            println!("[backend] {}", line);
                        }
                        tauri::api::process::CommandEvent::Stderr(line) => {
                            eprintln!("[backend] {}", line);
                        }
                        _ => {}
                    }
                }
            });

            #[cfg(debug_assertions)]
            {
                let window = app.get_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
