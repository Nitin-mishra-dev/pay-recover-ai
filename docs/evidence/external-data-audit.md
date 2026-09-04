# Forensic External Data Audit Report

**Date**: September 4, 2026  
**Audited Directories**:  
1. `razorpay_chargeback_ai_kaggle_export/`  
2. `razorpay_dispute_ai_dataset_v1/`  
**Auditor**: PayRecover AI Governance & Scientific Evaluation Kernel  
**Status**: **COMPLETED & EXCLUDED FROM CORE BENCHMARK & PUBLIC REPOSITORY**

---

## 1. Executive Verdict & Strategic Recommendation

* **Category**: **E. EXCLUDED from Core Model & Core Benchmark; Optional Offline Context Reference Only.**
* **Strategic Rationale**:
  1. **Domain Mismatch**: Both datasets represent post-delivery consumer chargeback disputes (goods not delivered, damaged goods, delivery delay) derived from historical 2017–2018 Brazilian e-commerce data (Olist) repackaged for RAG/chargeback workflows.
  2. **Track 03 Alignment**: Track 03 (*Autonomous Revenue & Payment Recovery*) explicitly centers on **post-failure payment recovery at transaction time** (bank network timeouts, 2FA abandonment, rail degradation, insufficient funds, and capture-race handling). Attempting to train or pivot the recovery engine onto consumer chargeback claims would divert the product into a post-facto risk dispute tool.
  3. **Repository Cleanliness**: The raw CSV files total **~85MB**. Committing them to Git would bloat the repository, risk distribution terms, and obscure the core 45-test deterministic engine. They have been permanently added to `.gitignore`.
  4. **Benchmark Integrity**: The verified PayRecover benchmark strictly preserves its **independent synthetic hidden physics world** with sealed holdouts (10,000 observations across 5 seeds). Introducing historical Olist chargeback logs would violate counterfactual simulation validity.

---

## 2. Dataset Forensic Breakdown

### Dataset A: `razorpay_chargeback_ai_kaggle_export`
* **Provenance**: Kaggle export (`himanshusharma809/razorpay-chargeback-ai-synthetic-dataset`).
* **License**: CC0-1.0 (Public Domain).
* **Domain**: Synthetic relational dataset created for consumer chargeback dispute resolution and RAG evidence retrieval.
* **Entities & Shapes**:
  * `customers.csv`: 10,000 rows × 8 columns (`customer_id`, `city`, `state`, `zip`, `region`, `name`, `email`, `phone`)
  * `merchants.csv`: 3,095 rows × 8 columns (`merchant_id`, `seller_city`, `seller_state`, `zip`, `region`, `name`, `email`, `phone`)
  * `orders.csv`: 99,441 rows × 11 columns (`order_id`, `order_status`, `purchase_timestamp`, `approved_at`, `delivered_date`, `delivery_delay_days`, `order_channel`)
  * `transactions.csv`: 103,886 rows × 8 columns (`transaction_id`, `payment_type`, `installments`, `payment_value`, `transaction_status`, `authorization_status`)
  * `deliveries.csv`: 99,441 rows × 9 columns (`delivery_id`, `order_id`, `carrier_date`, `estimated_delivery`, `delivery_delay_days`, `carrier_name`)
  * `disputes.csv`: 10,000 rows × 9 columns (`dispute_id`, `transaction_id`, `canonical_order_id`, `dispute_type`, `dispute_reason`, `dispute_amount`, `dispute_opened_at`, `dispute_status`, `claim`)

### Dataset B: `razorpay_dispute_ai_dataset_v1`
* **Provenance**: Local relational enrichment of Dataset A with foreign keys added to `orders.csv` (`customer_id`, `merchant_id`) and `transactions.csv` (`canonical_order_id`).
* **Size**: 103,886 transaction records; 10,000 dispute records.

---

## 3. Detailed Audit Matrix

| Forensic Dimension | Assessment & Findings |
| :--- | :--- |
| **File Types** | Flat CSV files and JSON metadata (`dataset-metadata.json`). |
| **Row Count** | 325,863 total relational rows across 6 entities. |
| **Label / Target Columns** | `dispute_status` (`open`, `resolved`, `under_review`), `dispute_reason` (`suspected_account_compromise`, `suspicious_transaction`). |
| **Missingness & Hygiene** | High completeness on primary keys; simulated dates span October 2017 to September 2018. |
| **PII Assessment** | Synthetic names (`Customer_0001`), synthetic emails (`customer1@example.com`), synthetic phone numbers (`+9198765...`). No real PII. |
| **Relevance to Track 03** | **Low to Moderate**. Disputed transactions represent already-captured payments undergoing refund contestation, not checkout-time recovery. |
| **Data Leakage Risk** | **High if used for recovery modeling**: Dispute labels occur weeks *after* payment capture; using them in checkout-time failure prediction would introduce severe target leakage. |
| **Train/Test Contamination** | **Critical Risk**: Integrating dispute tables into the synthetic holdout would contaminate the latent counterfactual generator. |
| **Inclusion in Public Repo** | **NO**. Excluded via `.gitignore` to maintain a lightweight, fast-cloning, professional competition repository. |

---

## 4. How PayRecover Safely Leverages Dispute Context (Without Retraining)

While the raw CSVs must not be used to train an ML model, the concept of **Dispute / Fraud State** is already authoritatively implemented in PayRecover's deterministic core:

1. **SafetyKernel Stage 5 Halt**: In [`src/core/safety_gate.py`](../../src/core/safety_gate.py) and [`tests/unit/test_safety_kernel.py`](../../tests/unit/test_safety_kernel.py), if a transaction is marked `DISPUTED` or flagged for fraud, all automated recovery interventions are **immediately blocked and frozen**.
2. **Economic Risk Penalty**: The IEV equation explicitly incorporates $\text{RiskPenalty}(a)$, penalizing intervention if dispute risk indicators are present.
3. **Audit Ledger Event**: Every dispute freeze generates a tamper-evident audit event (`AuditEventType.DISPUTE_FREEZE`).

---

## 5. Decision Summary

* **Core Model Data**: **REJECTED** (Preserves the 4 locked baselines and verified mathematical IEV optimization).
* **Public Repository Bloat**: **REJECTED** (Files ignored in `.gitignore`).
* **Operational Safety Guard**: **PRESERVED** (SafetyKernel maintains strict dispute-blocking invariants with 45/45 passing tests).
