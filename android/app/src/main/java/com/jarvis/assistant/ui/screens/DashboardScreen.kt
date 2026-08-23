package com.jarvis.assistant.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Checklist
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.jarvis.assistant.data.model.StatusResult
import com.jarvis.assistant.ui.components.AetherGlassCard
import com.jarvis.assistant.ui.components.ConnectionBadge
import com.jarvis.assistant.ui.components.EmergencyStopButton
import com.jarvis.assistant.ui.components.HealthScoreGauge
import com.jarvis.assistant.ui.theme.*
import com.jarvis.assistant.viewmodel.CompanionTab

@Composable
fun DashboardScreen(
    isConnected: Boolean,
    status: StatusResult?,
    healthScore: Double,
    onNavigateTab: (CompanionTab) -> Unit,
    onEmergencyStop: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Top Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "JARVIS HUD",
                    style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                    color = ElectricCyan
                )
                Text(
                    text = "Android Companion Client v0.8.1",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
            }
            ConnectionBadge(isConnected = isConnected)
        }

        // Health & Status Glass Card
        AetherGlassCard {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "System Overview",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Agent State: ${status?.agentState ?: "READY"}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = ElectricCyan
                    )
                    Text(
                        text = "Active Sessions: ${status?.activeSessions ?: 1}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary
                    )
                    Text(
                        text = "Pending Approvals: ${status?.pendingApprovals ?: 0}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if ((status?.pendingApprovals ?: 0) > 0) AuricGold else TextSecondary
                    )
                }
                HealthScoreGauge(score = healthScore)
            }
        }

        // Quick Navigation Tiles
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            ElevatedButton(
                onClick = { onNavigateTab(CompanionTab.CHAT) },
                modifier = Modifier.weight(1f).height(60.dp),
                colors = ButtonDefaults.elevatedButtonColors(
                    containerColor = DarkSurfaceElevated,
                    contentColor = ElectricCyan
                )
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Default.Chat, contentDescription = "Chat", tint = ElectricCyan)
                    Text("Chat", fontWeight = FontWeight.SemiBold)
                }
            }

            ElevatedButton(
                onClick = { onNavigateTab(CompanionTab.PROACTIVE) },
                modifier = Modifier.weight(1f).height(60.dp),
                colors = ButtonDefaults.elevatedButtonColors(
                    containerColor = DarkSurfaceElevated,
                    contentColor = AuricGold
                )
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Default.Lightbulb, contentDescription = "Advisory", tint = AuricGold)
                    Text("Advisory", fontWeight = FontWeight.SemiBold)
                }
            }
        }

        ElevatedButton(
            onClick = { onNavigateTab(CompanionTab.PLANS) },
            modifier = Modifier.fillMaxWidth().height(52.dp),
            colors = ButtonDefaults.elevatedButtonColors(
                containerColor = DarkSurfaceElevated,
                contentColor = TextPrimary
            )
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Default.Checklist, contentDescription = "Plans", tint = ElectricCyan)
                Text("Roadmaps & Milestones", fontWeight = FontWeight.SemiBold)
            }
        }

        Spacer(modifier = Modifier.weight(1f, fill = false))

        // Emergency Stop Control
        EmergencyStopButton(onClick = onEmergencyStop)
    }
}
