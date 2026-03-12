"""
Utility functions for car damage detection and price estimation
"""

import yaml
from pathlib import Path
from typing import Dict, Tuple, List


class DamagePriceEstimator:
    """
    Estimates repair/replacement prices for damaged car parts
    based on severity and Indian market prices
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.prices = self.config['prices']
        self.non_repairable = self.config['non_repairable_parts']
        self.severity_thresholds = self.config['damage_severity']
    
    def classify_severity(self, confidence: float) -> str:
        """
        Classify damage severity based on detection confidence
        
        Args:
            confidence: Detection confidence score (0-1)
        
        Returns:
            Severity level: 'low', 'medium', or 'high'
        """
        if confidence <= self.severity_thresholds['low']['confidence_max']:
            return 'low'
        elif confidence <= self.severity_thresholds['medium']['confidence_max']:
            return 'medium'
        else:
            return 'high'
    
    def estimate_price(self, part_name: str, confidence: float) -> Tuple[int, str, str]:
        """
        Estimate repair/replacement price for a damaged part
        
        Args:
            part_name: Name of the car part
            confidence: Detection confidence score
        
        Returns:
            Tuple of (price, action, severity)
            - price: Estimated cost in INR
            - action: 'repair' or 'replace'
            - severity: 'low', 'medium', or 'high'
        """
        severity = self.classify_severity(confidence)
        
        # Check if part is in price list
        if part_name not in self.prices:
            return 0, 'unknown', severity
        
        part_prices = self.prices[part_name]
        
        # Determine if part can be repaired or needs replacement
        if part_name in self.non_repairable:
            # Parts like headlight and windshield can only be replaced
            action = 'replace'
            price = part_prices.get(f'replace_{severity}', 0)
        else:
            # Other parts can be repaired for low/medium damage
            if severity == 'high':
                action = 'replace'
                price = part_prices.get('replace_high', 0)
            else:
                action = 'repair'
                price = part_prices.get(f'repair_{severity}', 0)
        
        return price, action, severity
    
    def calculate_total_estimate(self, detections: List[Dict]) -> Dict:
        """
        Calculate total repair estimate for all detected damages
        
        Args:
            detections: List of detection dictionaries with 'part', 'confidence'
        
        Returns:
            Dictionary with detailed breakdown and total cost
        """
        results = {
            'damages': [],
            'total_cost': 0,
            'total_parts': len(detections),
            'repairable': 0,
            'replaceable': 0
        }
        
        for detection in detections:
            part_name = detection.get('part', 'unknown')
            confidence = detection.get('confidence', 0.0)
            detailed_part = detection.get('detailed_part', part_name)  # Get detailed part name
            
            price, action, severity = self.estimate_price(part_name, confidence)
            
            damage_info = {
                'part': part_name,
                'detailed_part': detailed_part,  # Add detailed part name
                'severity': severity,
                'action': action,
                'price': price,
                'confidence': round(confidence, 2),
                'description': self.severity_thresholds[severity]['description']
            }
            
            results['damages'].append(damage_info)
            results['total_cost'] += price
            
            if action == 'repair':
                results['repairable'] += 1
            else:
                results['replaceable'] += 1
        
        return results
    
    def get_severity_description(self, severity: str) -> str:
        """Get description for severity level"""
        return self.severity_thresholds.get(severity, {}).get('description', 'Unknown')


def load_config(config_path: str = "config.yaml") -> Dict:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file
    
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def format_currency(amount: int) -> str:
    """
    Format amount in Indian currency format
    
    Args:
        amount: Amount in INR
    
    Returns:
        Formatted string (e.g., "₹ 5,000")
    """
    return f"₹ {amount:,}"


def get_part_color_code(severity: str) -> str:
    """
    Get color code for severity level (for visualization)
    
    Args:
        severity: Severity level
    
    Returns:
        Color code in hex
    """
    colors = {
        'low': '#90EE90',      # Light green
        'medium': '#FFD700',   # Gold
        'high': '#FF6347'      # Tomato red
    }
    return colors.get(severity, '#FFFFFF')


if __name__ == "__main__":
    # Test the estimator
    estimator = DamagePriceEstimator()
    
    # Example detections
    test_detections = [
        {'part': 'bumper', 'confidence': 0.35},      # Low severity
        {'part': 'door', 'confidence': 0.65},        # Medium severity
        {'part': 'headlight', 'confidence': 0.85},   # High severity, must replace
        {'part': 'hood', 'confidence': 0.45},        # Low severity
    ]
    
    results = estimator.calculate_total_estimate(test_detections)
    
    print("\n" + "=" * 60)
    print("Price Estimation Test")
    print("=" * 60)
    
    for damage in results['damages']:
        print(f"\nPart: {damage['part'].upper()}")
        print(f"  Severity: {damage['severity']}")
        print(f"  Action: {damage['action']}")
        print(f"  Price: {format_currency(damage['price'])}")
        print(f"  Confidence: {damage['confidence']}")
    
    print("\n" + "=" * 60)
    print(f"Total Estimated Cost: {format_currency(results['total_cost'])}")
    print(f"Parts to Repair: {results['repairable']}")
    print(f"Parts to Replace: {results['replaceable']}")
    print("=" * 60)
