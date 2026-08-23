package com.jarvis.assistant.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.jarvis.assistant.data.model.ProactiveAdvisoryDto
import com.jarvis.assistant.ui.components.AetherGlassCard
import com.jarvis.assistant.ui.components.HealthScoreGauge
import com.jarvis.assistant.ui.theme.*

@Composable
fun ProactiveScreen(
    advisory: ProactiveAdvisoryDto?,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "Proactive Intelligence",
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            color = AuricGold
        )
        Text(
            text = "Continuous automated project review, epistemic verification, and architecture health monitoring.",
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary
        )

        // Health Score Card
        AetherGlassCard(borderColor = AuricGold.copy(alpha = 0.4f)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Project Health Assessment",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = TextPrimary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Security Findings: ${advisory?.findingsCount ?: 0}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if ((advisory?.findingsCount ?: 0) > 0) DangerCrimson else ElectricCyan
                    )
                    Text(
                        text = "Proactive Suggestions: ${advisory?.suggestionsCount ?: 0}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = AuricGold
                    )
                }
                HealthScoreGauge(score = advisory?.healthScore ?: 100.0)
            }
        }

        // Observations List
        Text(
            text = "Recent Observations",
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
            color = TextPrimary
        )

        if (advisory?.observations.isNullOrEmpty()) {
            AetherGlassCard {
                Text(
                    text = "No proactive alerts or observations pending. All repository subsystems are nominal.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
            }
        } else {
            advisory?.observations?.forEach { obs ->
                AetherGlassCard {
                    Text(
                        text = "• $obs",
                        style = MaterialTheme.typography.bodyLarge,
                        color = TextPrimary
                    )
                }
            }
        }
    }
}
