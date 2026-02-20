"""
Calculator module for finance calculations
"""

from decimal import Decimal, ROUND_HALF_UP
from .models import Invoice, Payment, FeeStructure
from django.utils import timezone


class FeeCalculator:
    """Calculator for fee-related calculations"""
    
    @staticmethod
    def calculate_late_penalty(invoice, penalty_rate=0.02):
        """Calculate late payment penalty"""
        if invoice.due_date and invoice.balance > 0:
            days_overdue = (timezone.now().date() - invoice.due_date).days
            if days_overdue > 0:
                penalty = invoice.balance * penalty_rate * (days_overdue / 30)
                return penalty.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')
    
    @staticmethod
    def calculate_installment_plan(total_amount, num_installments, interest_rate=0):
        """Calculate installment payment plan"""
        if interest_rate > 0:
            total_with_interest = total_amount * (1 + interest_rate)
        else:
            total_with_interest = total_amount
        
        installment_amount = total_with_interest / num_installments
        
        installments = []
        for i in range(1, num_installments + 1):
            installments.append({
                'installment_number': i,
                'due_date': timezone.now().date() + timezone.timedelta(days=30 * i),
                'amount': installment_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            })
        
        return {
            'total_amount': total_amount,
            'total_with_interest': total_with_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'interest_rate': interest_rate,
            'num_installments': num_installments,
            'installment_amount': installment_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'installments': installments
        }
    
    @staticmethod
    def calculate_bulk_discount(amount, student_count, discount_tiers):
        """Calculate bulk registration discount"""
        # discount_tiers: [(min_students, discount_percentage), ...]
        discount_percentage = 0
        
        for min_students, discount in sorted(discount_tiers, reverse=True):
            if student_count >= min_students:
                discount_percentage = discount
                break
        
        discount_amount = amount * (discount_percentage / 100)
        return {
            'original_amount': amount,
            'discount_percentage': discount_percentage,
            'discount_amount': discount_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'final_amount': (amount - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }

class BudgetCalculator:
    """Calculator for budget-related calculations"""
    
    @staticmethod
    def calculate_budget_variance(allocated, spent):
        """Calculate budget variance"""
        variance = allocated - spent
        variance_percentage = (variance / allocated * 100) if allocated > 0 else 0
        
        return {
            'allocated': allocated,
            'spent': spent,
            'variance': variance,
            'variance_percentage': variance_percentage,
            'status': 'under_budget' if variance >= 0 else 'over_budget'
        }
    
    @staticmethod
    def forecast_budget(historical_data, growth_rate=0.05):
        """Forecast budget based on historical data"""
        if not historical_data:
            return None
        
        average = sum(historical_data) / len(historical_data)
        forecast = average * (1 + growth_rate)
        
        return {
            'historical_average': average,
            'growth_rate': growth_rate,
            'forecast': forecast
        }

class TaxCalculator:
    """Calculator for tax-related calculations"""
    
    # Kenyan tax bands (simplified)
    TAX_BANDS = [
        (24000, 0.10),  # 10% for first 24,000
        (32333, 0.25),  # 25% for next 32,333
        (float('inf'), 0.30)  # 30% for remainder
    ]
    
    @staticmethod
    def calculate_paye(monthly_income):
        """Calculate PAYE tax"""
        tax = 0
        remaining_income = monthly_income
        
        for band_limit, rate in TaxCalculator.TAX_BANDS:
            if remaining_income <= 0:
                break
            
            taxable = min(remaining_income, band_limit)
            tax += taxable * rate
            remaining_income -= taxable
        
        # Personal relief (simplified)
        personal_relief = 2400
        tax = max(0, tax - personal_relief)
        
        return tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_nssf(gross_pay):
        """Calculate NSSF contribution"""
        # Simplified NSSF calculation
        tier1 = min(gross_pay, 6000) * 0.06
        tier2 = max(0, min(gross_pay, 18000) - 6000) * 0.06
        
        return {
            'tier1': tier1.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'tier2': tier2.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total': (tier1 + tier2).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    @staticmethod
    def calculate_nhif(gross_pay):
        """Calculate NHIF contribution"""
        # Simplified NHIF bands
        bands = [
            (5999, 150),
            (7999, 300),
            (11999, 400),
            (14999, 500),
            (19999, 600),
            (24999, 750),
            (29999, 850),
            (34999, 900),
            (39999, 950),
            (44999, 1000),
            (49999, 1100),
            (59999, 1200),
            (69999, 1300),
            (79999, 1400),
            (89999, 1500),
            (99999, 1600),
            (float('inf'), 1700)
        ]
        
        for band_limit, contribution in bands:
            if gross_pay <= band_limit:
                return Decimal(contribution)
        
        return Decimal(1700)