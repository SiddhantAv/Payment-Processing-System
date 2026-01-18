"""
Authorize.Net payment gateway repository.
Implements payment processing using Authorize.Net official SDK.
"""
import uuid
from decimal import Decimal
from typing import Optional
from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from authorizenet.constants import constants
from app.core.config import settings
from app.repositories.payment_gateway.gateway_interface import PaymentGatewayInterface, GatewayResult
from app.exceptions.payment_exceptions import GatewayError, PaymentDeclinedError, InvalidCardError


class AuthorizeNetRepository(PaymentGatewayInterface):
    """Repository for Authorize.Net payment gateway operations."""
    
    def __init__(self):
        """Initialize Authorize.Net repository with credentials from settings."""
        self.api_login_id = settings.AUTHORIZE_NET_API_LOGIN_ID
        self.transaction_key = settings.AUTHORIZE_NET_TRANSACTION_KEY
        self.environment = (
            constants.SANDBOX if settings.AUTHORIZE_NET_ENVIRONMENT == "sandbox"
            else constants.PRODUCTION
        )
        
        if not self.api_login_id or not self.transaction_key:
            raise ValueError("Authorize.Net credentials not configured")
    
    def charge_card(
        self,
        amount: Decimal,
        currency: str,
        card_number: str,
        expiry_month: int,
        expiry_year: int,
        cvv: str
    ) -> GatewayResult:
        """
        Charge a credit card (authorize + capture in one step).
        
        Args:
            amount: Transaction amount
            currency: Currency code (e.g., "USD")
            card_number: Credit card number
            expiry_month: Card expiration month (1-12)
            expiry_year: Card expiration year (4 digits)
            cvv: Card CVV code
            
        Returns:
            GatewayResult with transaction details
            
        Raises:
            InvalidCardError: If card details are invalid
            PaymentDeclinedError: If payment is declined
            GatewayError: If gateway returns an error
        """
        try:
            # Create merchant authentication
            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key
            
            # Create credit card object
            credit_card = apicontractsv1.creditCardType()
            credit_card.cardNumber = card_number.replace(" ", "").replace("-", "")
            credit_card.expirationDate = f"{expiry_year:04d}-{expiry_month:02d}"
            credit_card.cardCode = cvv
            
            # Create payment object
            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card
            
            # Create transaction request
            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "authCaptureTransaction"
            transaction_request.amount = f"{amount:.2f}"
            transaction_request.payment = payment
            
            # Create API request
            api_request = apicontractsv1.createTransactionRequest()
            api_request.merchantAuthentication = merchant_auth
            # Generate unique refId to prevent duplicate transaction errors
            # Authorize.Net uses refId + amount + card to detect duplicates within ~120 seconds
            api_request.refId = f"PPS-{uuid.uuid4().hex[:16]}"  # Unique reference ID for tracking
            api_request.transactionRequest = transaction_request
            
            # Create controller and execute
            controller = createTransactionController(api_request)
            controller.setenvironment(self.environment)
            controller.execute()
            
            # Get response
            response = controller.getresponse()
            
            if response is None:
                raise GatewayError("No response from payment gateway")
            
            # Check if messages exist
            if not hasattr(response, 'messages') or response.messages is None:
                raise GatewayError("Invalid response from payment gateway: no messages")
            
            # Check response code
            if response.messages.resultCode == "Ok":
                # Transaction approved
                transaction_response = response.transactionResponse
                
                if transaction_response is None:
                    raise GatewayError("Transaction response is missing")
                
                # Convert responseCode to string for comparison (handles both "1" and 1)
                response_code = str(transaction_response.responseCode).strip()
                
                if response_code == "1":  # Approved
                    message = "Transaction approved"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        message = str(transaction_response.messages.message[0].description or "Transaction approved")
                    # Convert transId to string to avoid lxml.objectify type issues
                    trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                    return GatewayResult(
                        success=True,
                        transaction_id=trans_id,
                        message=message
                    )
                elif response_code == "2":  # Declined
                    error_text = "Payment declined"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Payment declined")
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Payment declined")
                    raise PaymentDeclinedError(error_text)
                else:
                    # Check if the message indicates approval despite unexpected responseCode
                    error_text = "Transaction error"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Transaction error")
                        # If message says "approved", treat as success
                        if "approved" in error_text.lower():
                            # Convert transId to string to avoid lxml.objectify type issues
                            trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                            return GatewayResult(
                                success=True,
                                transaction_id=trans_id,
                                message=error_text
                            )
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Transaction error")
                    raise GatewayError(error_text)
            else:
                # API-level error - extract detailed error message
                error_message = "Gateway error"
                
                # Try to get error from messages
                if hasattr(response.messages, 'message') and len(response.messages.message) > 0:
                    for msg in response.messages.message:
                        if hasattr(msg, 'text') and msg.text is not None:
                            error_message = str(msg.text)
                            break
                
                # Try to get error from transactionResponse if available
                if hasattr(response, 'transactionResponse') and response.transactionResponse is not None:
                    if hasattr(response.transactionResponse, 'errors') and response.transactionResponse.errors is not None:
                        if hasattr(response.transactionResponse.errors, 'error') and len(response.transactionResponse.errors.error) > 0:
                            error_text = response.transactionResponse.errors.error[0].errorText
                            if error_text is not None:
                                error_message = str(error_text)
                    elif hasattr(response.transactionResponse, 'messages') and response.transactionResponse.messages is not None:
                        if hasattr(response.transactionResponse.messages, 'message') and len(response.transactionResponse.messages.message) > 0:
                            error_desc = response.transactionResponse.messages.message[0].description
                            if error_desc is not None:
                                error_message = str(error_desc)
                
                # Ensure error_message is a string before calling .lower()
                error_message = str(error_message) if error_message else "Gateway error"
                
                # Check if it's a card validation error
                if error_message and ("card" in error_message.lower() or "invalid" in error_message.lower()):
                    raise InvalidCardError(error_message)
                
                raise GatewayError(error_message)
                
        except (InvalidCardError, PaymentDeclinedError, GatewayError):
            # Re-raise payment-specific exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise GatewayError(f"Unexpected gateway error: {str(e)}")

    def authorize_card(
        self,
        amount: Decimal,
        currency: str,
        card_number: str,
        expiry_month: int,
        expiry_year: int,
        cvv: str
    ) -> GatewayResult:
        """
        Authorize a credit card without capturing funds.

        Args:
            amount: Transaction amount
            currency: Currency code (e.g., "USD")
            card_number: Credit card number
            expiry_month: Card expiration month (1-12)
            expiry_year: Card expiration year (4 digits)
            cvv: Card CVV code

        Returns:
            GatewayResult with transaction details

        Raises:
            InvalidCardError: If card details are invalid
            PaymentDeclinedError: If payment is declined
            GatewayError: If gateway returns an error
        """
        try:
            # Create merchant authentication
            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key

            # Create credit card object
            credit_card = apicontractsv1.creditCardType()
            credit_card.cardNumber = card_number.replace(" ", "").replace("-", "")
            credit_card.expirationDate = f"{expiry_year:04d}-{expiry_month:02d}"
            credit_card.cardCode = cvv

            # Create payment object
            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card

            # Create transaction request (authorize only)
            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "authOnlyTransaction"
            transaction_request.amount = f"{amount:.2f}"
            transaction_request.payment = payment

            # Create API request
            api_request = apicontractsv1.createTransactionRequest()
            api_request.merchantAuthentication = merchant_auth
            # Generate unique refId to prevent duplicate transaction errors
            # Authorize.Net uses refId + amount + card to detect duplicates within ~120 seconds
            api_request.refId = f"PPS-{uuid.uuid4().hex[:16]}"  # Unique reference ID for tracking
            api_request.transactionRequest = transaction_request

            # Create controller and execute
            controller = createTransactionController(api_request)
            controller.setenvironment(self.environment)
            controller.execute()

            # Get response
            response = controller.getresponse()

            if response is None:
                raise GatewayError("No response from payment gateway")
            
            # Check if messages exist
            if not hasattr(response, 'messages') or not response.messages:
                raise GatewayError("Invalid response from payment gateway: no messages")

            # Check response code
            if response.messages.resultCode == "Ok":
                # Transaction approved
                transaction_response = response.transactionResponse

                if transaction_response is None:
                    raise GatewayError("Transaction response is missing")

                # Convert responseCode to string for comparison (handles both "1" and 1)
                response_code = str(transaction_response.responseCode).strip()
                
                if response_code == "1":  # Approved
                    message = "Authorization approved"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        message = str(transaction_response.messages.message[0].description or "Authorization approved")
                    # Convert transId to string to avoid lxml.objectify type issues
                    trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                    return GatewayResult(
                        success=True,
                        transaction_id=trans_id,
                        message=message
                    )
                elif response_code == "2":  # Declined
                    error_text = "Authorization declined"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Authorization declined")
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Authorization declined")
                    raise PaymentDeclinedError(error_text)
                else:
                    # Check if the message indicates approval despite unexpected responseCode
                    error_text = "Authorization error"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Authorization error")
                        # If message says "approved", treat as success
                        if "approved" in error_text.lower():
                            # Convert transId to string to avoid lxml.objectify type issues
                            trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                            return GatewayResult(
                                success=True,
                                transaction_id=trans_id,
                                message=error_text
                            )
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Authorization error")
                    raise GatewayError(error_text)
            else:
                # API-level error - extract detailed error message
                error_message = "Gateway error"
                
                # Try to get error from messages
                if hasattr(response.messages, 'message') and len(response.messages.message) > 0:
                    for msg in response.messages.message:
                        if hasattr(msg, 'text') and msg.text is not None:
                            error_message = str(msg.text)
                            break
                
                # Try to get error from transactionResponse if available
                if hasattr(response, 'transactionResponse') and response.transactionResponse is not None:
                    if hasattr(response.transactionResponse, 'errors') and response.transactionResponse.errors is not None:
                        if hasattr(response.transactionResponse.errors, 'error') and len(response.transactionResponse.errors.error) > 0:
                            error_text = response.transactionResponse.errors.error[0].errorText
                            if error_text is not None:
                                error_message = str(error_text)
                    elif hasattr(response.transactionResponse, 'messages') and response.transactionResponse.messages is not None:
                        if hasattr(response.transactionResponse.messages, 'message') and len(response.transactionResponse.messages.message) > 0:
                            error_desc = response.transactionResponse.messages.message[0].description
                            if error_desc is not None:
                                error_message = str(error_desc)

                # Ensure error_message is a string before calling .lower()
                error_message = str(error_message) if error_message else "Gateway error"

                # Check if it's a card validation error
                if error_message and ("card" in error_message.lower() or "invalid" in error_message.lower()):
                    raise InvalidCardError(error_message)

                raise GatewayError(error_message)

        except (InvalidCardError, PaymentDeclinedError, GatewayError):
            # Re-raise payment-specific exceptions
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise GatewayError(f"Unexpected gateway error: {str(e)}")

    def capture_transaction(
        self,
        gateway_transaction_id: str,
        amount: Decimal
    ) -> GatewayResult:
        """
        Capture a previously authorized transaction.

        Args:
            gateway_transaction_id: Gateway transaction ID from authorization
            amount: Capture amount

        Returns:
            GatewayResult with transaction details

        Raises:
            GatewayError: If gateway returns an error
        """
        try:
            # Create merchant authentication
            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key

            # Create transaction request (prior auth capture)
            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "priorAuthCaptureTransaction"
            transaction_request.amount = f"{amount:.2f}"
            transaction_request.refTransId = gateway_transaction_id

            # Create API request
            api_request = apicontractsv1.createTransactionRequest()
            api_request.merchantAuthentication = merchant_auth
            # Generate unique refId to prevent duplicate transaction errors
            api_request.refId = f"PPS-{uuid.uuid4().hex[:16]}"
            api_request.transactionRequest = transaction_request

            # Create controller and execute
            controller = createTransactionController(api_request)
            controller.setenvironment(self.environment)
            controller.execute()

            # Get response
            response = controller.getresponse()

            if response is None:
                raise GatewayError("No response from payment gateway")

            # Check if messages exist
            if not hasattr(response, 'messages') or response.messages is None:
                raise GatewayError("Invalid response from payment gateway: no messages")

            # Check response code
            if response.messages.resultCode == "Ok":
                transaction_response = response.transactionResponse

                if transaction_response is None:
                    raise GatewayError("Transaction response is missing")

                response_code = str(transaction_response.responseCode).strip()

                if response_code == "1":  # Approved
                    message = "Capture approved"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        message = str(transaction_response.messages.message[0].description or "Capture approved")
                    trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                    return GatewayResult(
                        success=True,
                        transaction_id=trans_id,
                        message=message
                    )
                elif response_code == "2":  # Declined
                    error_text = "Capture declined"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Capture declined")
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Capture declined")
                    raise GatewayError(error_text)
                else:
                    error_text = "Capture error"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Capture error")
                        if "approved" in error_text.lower():
                            trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                            return GatewayResult(
                                success=True,
                                transaction_id=trans_id,
                                message=error_text
                            )
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Capture error")
                    raise GatewayError(error_text)
            else:
                error_message = "Gateway error"

                if hasattr(response.messages, 'message') and len(response.messages.message) > 0:
                    for msg in response.messages.message:
                        if hasattr(msg, 'text') and msg.text is not None:
                            error_message = str(msg.text)
                            break

                if hasattr(response, 'transactionResponse') and response.transactionResponse is not None:
                    if hasattr(response.transactionResponse, 'errors') and response.transactionResponse.errors is not None:
                        if hasattr(response.transactionResponse.errors, 'error') and len(response.transactionResponse.errors.error) > 0:
                            error_text = response.transactionResponse.errors.error[0].errorText
                            if error_text is not None:
                                error_message = str(error_text)
                    elif hasattr(response.transactionResponse, 'messages') and response.transactionResponse.messages is not None:
                        if hasattr(response.transactionResponse.messages, 'message') and len(response.transactionResponse.messages.message) > 0:
                            error_desc = response.transactionResponse.messages.message[0].description
                            if error_desc is not None:
                                error_message = str(error_desc)

                error_message = str(error_message) if error_message else "Gateway error"
                raise GatewayError(error_message)

        except GatewayError:
            raise
        except Exception as e:
            raise GatewayError(f"Unexpected gateway error: {str(e)}")

    def void_transaction(
        self,
        gateway_transaction_id: str
    ) -> GatewayResult:
        """
        Void a previously authorized transaction (no capture).

        Args:
            gateway_transaction_id: Gateway transaction ID from authorization

        Returns:
            GatewayResult with transaction details

        Raises:
            GatewayError: If gateway returns an error
        """
        try:
            # Create merchant authentication
            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key

            # Create transaction request (void)
            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "voidTransaction"
            transaction_request.refTransId = gateway_transaction_id

            # Create API request
            api_request = apicontractsv1.createTransactionRequest()
            api_request.merchantAuthentication = merchant_auth
            api_request.refId = f"PPS-{uuid.uuid4().hex[:16]}"
            api_request.transactionRequest = transaction_request

            # Create controller and execute
            controller = createTransactionController(api_request)
            controller.setenvironment(self.environment)
            controller.execute()

            # Get response
            response = controller.getresponse()

            if response is None:
                raise GatewayError("No response from payment gateway")

            if not hasattr(response, 'messages') or response.messages is None:
                raise GatewayError("Invalid response from payment gateway: no messages")

            if response.messages.resultCode == "Ok":
                transaction_response = response.transactionResponse

                if transaction_response is None:
                    raise GatewayError("Transaction response is missing")

                response_code = str(transaction_response.responseCode).strip()

                if response_code == "1":  # Approved
                    message = "Void approved"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        message = str(transaction_response.messages.message[0].description or "Void approved")
                    trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                    return GatewayResult(
                        success=True,
                        transaction_id=trans_id,
                        message=message
                    )
                elif response_code == "2":  # Declined
                    error_text = "Void declined"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Void declined")
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Void declined")
                    raise GatewayError(error_text)
                else:
                    error_text = "Void error"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Void error")
                        if "approved" in error_text.lower():
                            trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                            return GatewayResult(
                                success=True,
                                transaction_id=trans_id,
                                message=error_text
                            )
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Void error")
                    raise GatewayError(error_text)
            else:
                error_message = "Gateway error"

                if hasattr(response.messages, 'message') and len(response.messages.message) > 0:
                    for msg in response.messages.message:
                        if hasattr(msg, 'text') and msg.text is not None:
                            error_message = str(msg.text)
                            break

                if hasattr(response, 'transactionResponse') and response.transactionResponse is not None:
                    if hasattr(response.transactionResponse, 'errors') and response.transactionResponse.errors is not None:
                        if hasattr(response.transactionResponse.errors, 'error') and len(response.transactionResponse.errors.error) > 0:
                            error_text = response.transactionResponse.errors.error[0].errorText
                            if error_text is not None:
                                error_message = str(error_text)
                    elif hasattr(response.transactionResponse, 'messages') and response.transactionResponse.messages is not None:
                        if hasattr(response.transactionResponse.messages, 'message') and len(response.transactionResponse.messages.message) > 0:
                            error_desc = response.transactionResponse.messages.message[0].description
                            if error_desc is not None:
                                error_message = str(error_desc)

                error_message = str(error_message) if error_message else "Gateway error"
                raise GatewayError(error_message)

        except GatewayError:
            raise
        except Exception as e:
            raise GatewayError(f"Unexpected gateway error: {str(e)}")

    def refund_transaction(
        self,
        gateway_transaction_id: str,
        amount: Decimal,
        last_four: str,
        expiry_month: int,
        expiry_year: int
    ) -> GatewayResult:
        """
        Refund a previously captured transaction.

        Args:
            gateway_transaction_id: Gateway transaction ID from capture
            amount: Refund amount
            last_four: Last four digits of the card
            expiry_month: Card expiration month (1-12)
            expiry_year: Card expiration year (4 digits)

        Returns:
            GatewayResult with transaction details

        Raises:
            GatewayError: If gateway returns an error
        """
        try:
            # Create merchant authentication
            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key

            # Create credit card object with last four and expiry
            # For refunds, Authorize.Net requires the last 4 digits of the card
            credit_card = apicontractsv1.creditCardType()
            # Ensure last_four is exactly 4 digits (pad with zeros if needed)
            last_four_formatted = str(last_four).strip()[-4:].zfill(4)
            credit_card.cardNumber = last_four_formatted
            credit_card.expirationDate = f"{expiry_year:04d}-{expiry_month:02d}"

            # Create payment object
            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card

            # Create transaction request (refund)
            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "refundTransaction"
            transaction_request.amount = f"{amount:.2f}"
            transaction_request.payment = payment
            transaction_request.refTransId = gateway_transaction_id

            # Create API request
            api_request = apicontractsv1.createTransactionRequest()
            api_request.merchantAuthentication = merchant_auth
            api_request.refId = f"PPS-{uuid.uuid4().hex[:16]}"
            api_request.transactionRequest = transaction_request

            # Create controller and execute
            controller = createTransactionController(api_request)
            controller.setenvironment(self.environment)
            controller.execute()

            # Get response
            response = controller.getresponse()

            if response is None:
                raise GatewayError("No response from payment gateway")

            if not hasattr(response, 'messages') or response.messages is None:
                raise GatewayError("Invalid response from payment gateway: no messages")

            if response.messages.resultCode == "Ok":
                transaction_response = response.transactionResponse

                if transaction_response is None:
                    raise GatewayError("Transaction response is missing")

                response_code = str(transaction_response.responseCode).strip()

                if response_code == "1":  # Approved
                    message = "Refund approved"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        message = str(transaction_response.messages.message[0].description or "Refund approved")
                    trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                    return GatewayResult(
                        success=True,
                        transaction_id=trans_id,
                        message=message
                    )
                elif response_code == "2":  # Declined
                    error_text = "Refund declined"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Refund declined")
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Refund declined")
                    raise GatewayError(error_text)
                else:
                    error_text = "Refund error"
                    if transaction_response.messages and hasattr(transaction_response.messages, 'message') and len(transaction_response.messages.message) > 0:
                        error_text = str(transaction_response.messages.message[0].description or "Refund error")
                        if "approved" in error_text.lower():
                            trans_id = str(transaction_response.transId) if transaction_response.transId is not None else None
                            return GatewayResult(
                                success=True,
                                transaction_id=trans_id,
                                message=error_text
                            )
                    elif hasattr(transaction_response, 'errors') and transaction_response.errors and hasattr(transaction_response.errors, 'error') and len(transaction_response.errors.error) > 0:
                        error_text = str(transaction_response.errors.error[0].errorText or "Refund error")
                    raise GatewayError(error_text)
            else:
                error_message = "Gateway error"

                if hasattr(response.messages, 'message') and len(response.messages.message) > 0:
                    for msg in response.messages.message:
                        if hasattr(msg, 'text') and msg.text is not None:
                            error_message = str(msg.text)
                            break

                if hasattr(response, 'transactionResponse') and response.transactionResponse is not None:
                    if hasattr(response.transactionResponse, 'errors') and response.transactionResponse.errors is not None:
                        if hasattr(response.transactionResponse.errors, 'error') and len(response.transactionResponse.errors.error) > 0:
                            error_text = response.transactionResponse.errors.error[0].errorText
                            if error_text is not None:
                                error_message = str(error_text)
                    elif hasattr(response.transactionResponse, 'messages') and response.transactionResponse.messages is not None:
                        if hasattr(response.transactionResponse.messages, 'message') and len(response.transactionResponse.messages.message) > 0:
                            error_desc = response.transactionResponse.messages.message[0].description
                            if error_desc is not None:
                                error_message = str(error_desc)

                error_message = str(error_message) if error_message else "Gateway error"
                raise GatewayError(error_message)

        except GatewayError:
            raise
        except Exception as e:
            raise GatewayError(f"Unexpected gateway error: {str(e)}")
