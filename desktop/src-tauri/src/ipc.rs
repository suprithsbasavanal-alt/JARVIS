//! Unix Domain Socket JSON-RPC 2.0 IPC Client for JARVIS Core.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::PathBuf;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

const DEFAULT_SOCKET_PATH: &str = "/tmp/jarvis_daemon.sock";

#[derive(Debug, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: String,
    pub method: String,
    pub params: Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    pub data: Option<Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<String>,
    pub result: Option<Value>,
    pub error: Option<JsonRpcError>,
}

pub struct IpcClient {
    socket_path: PathBuf,
    auth_token: String,
}

impl IpcClient {
    pub fn new(socket_path: Option<PathBuf>, auth_token: String) -> Self {
        Self {
            socket_path: socket_path.unwrap_or_else(|| PathBuf::from(DEFAULT_SOCKET_PATH)),
            auth_token,
        }
    }

    pub async fn call(&self, method: &str, params: Value) -> Result<Value, String> {
        let stream = UnixStream::connect(&self.socket_path)
            .await
            .map_err(|e| format!("Failed to connect to JARVIS daemon at {:?}: {}", self.socket_path, e))?;

        let (reader, mut writer) = stream.into_split();
        let mut buf_reader = BufReader::new(reader);

        // 1. Perform Authentication Handshake
        let handshake_req = json!({
            "jsonrpc": "2.0",
            "id": uuid::Uuid::new_v4().to_string(),
            "method": "jarvis.handshake",
            "params": {
                "auth_token": self.auth_token
            }
        });

        let mut req_str = serde_json::to_string(&handshake_req).map_err(|e| e.to_string())?;
        req_str.push('\n');
        writer.write_all(req_str.as_bytes()).await.map_err(|e| e.to_string())?;
        writer.flush().await.map_err(|e| e.to_string())?;

        let mut line = String::new();
        buf_reader.read_line(&mut line).await.map_err(|e| e.to_string())?;
        let handshake_resp: JsonRpcResponse = serde_json::from_str(&line).map_err(|e| e.to_string())?;

        if let Some(err) = handshake_resp.error {
            return Err(format!("Daemon handshake failed: {}", err.message));
        }

        // 2. Execute target method
        let target_req = json!({
            "jsonrpc": "2.0",
            "id": uuid::Uuid::new_v4().to_string(),
            "method": method,
            "params": params
        });

        let mut target_str = serde_json::to_string(&target_req).map_err(|e| e.to_string())?;
        target_str.push('\n');
        writer.write_all(target_str.as_bytes()).await.map_err(|e| e.to_string())?;
        writer.flush().await.map_err(|e| e.to_string())?;

        line.clear();
        buf_reader.read_line(&mut line).await.map_err(|e| e.to_string())?;
        let resp: JsonRpcResponse = serde_json::from_str(&line).map_err(|e| e.to_string())?;

        if let Some(err) = resp.error {
            return Err(format!("JSON-RPC Error [{}]: {}", err.code, err.message));
        }

        resp.result.ok_or_else(|| "Empty result received from JARVIS daemon".to_string())
    }
}
