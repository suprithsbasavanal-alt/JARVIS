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
import com.jarvis.assistant.data.model.StructuredPlanDto
import com.jarvis.assistant.ui.components.AetherGlassCard
import com.jarvis.assistant.ui.theme.*

@Composable
fun PlanScreen(
    plan: StructuredPlanDto?,
    onToggleStep: (planId: String, stepNumber: Int, currentCompleted: Boolean) -> Unit,
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
            text = "Active Roadmap & Checklists",
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            color = ElectricCyan
        )

        if (plan == null) {
            AetherGlassCard {
                Text(
                    text = "No active structured plans found.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )
            }
        } else {
            // Plan Overview Card
            AetherGlassCard(borderColor = ElectricCyan.copy(alpha = 0.5f)) {
                Text(
                    text = plan.title,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = ElectricCyan
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = plan.goal,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextPrimary
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Category: ${plan.category} • Est. Hours: ${plan.estimatedHours ?: 0.0}h",
                    style = MaterialTheme.typography.labelSmall,
                    color = AuricGold
                )
            }

            // Milestones & Steps
            plan.milestones.forEach { milestone ->
                Text(
                    text = milestone.title,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                    color = TextPrimary
                )

                milestone.steps.forEach { step ->
                    AetherGlassCard {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Checkbox(
                                checked = step.isCompleted,
                                onCheckedChange = {
                                    onToggleStep(plan.planId, step.stepNumber, step.isCompleted)
                                },
                                colors = CheckboxDefaults.colors(
                                    checkedColor = ElectricCyan,
                                    uncheckedColor = TextSecondary,
                                    checkmarkColor = DarkVoid
                                )
                            )

                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "Step ${step.stepNumber}: ${step.description}",
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = if (step.isCompleted) TextSecondary else TextPrimary
                                )
                                Text(
                                    text = "Deliverable: ${step.deliverable}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (step.isCompleted) TextMuted else AuricGold
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
