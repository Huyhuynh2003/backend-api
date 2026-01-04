from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pathlib import Path

conf = ConnectionConfig(
    MAIL_USERNAME = "huyhuynh290423@gmail.com",
    MAIL_PASSWORD = "ljlt adaz zjmb ekig",  # Gmail App Password
    MAIL_FROM = "huyhuynh290423@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME = "Hệ thống đặt lịch khám",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
)

fast_mail = FastMail(conf)


async def send_appointment_email(
    email: str,
    patient_name: str,
    doctor_name: str,
    appointment_date,
    appointment_time,
    status: str,
    note: str = ""
):
    if status == "confirmed":
        subject = "Lịch khám của bạn đã được xác nhận"
        body = f"""
        <h3>Xin chào {patient_name}</h3>
        <p>Lịch khám của bạn đã được <b>bác sĩ {doctor_name}</b> xác nhận.</p>
        <p><b>Ngày:</b> {appointment_date}</p>
        <p><b>Giờ:</b> {appointment_time}</p>
        <p>Vui lòng đến đúng giờ.</p>
        """
    else:
        subject = "Lịch khám của bạn đã bị từ chối"
        body = f"""
        <h3>Xin chào {patient_name}</h3>
        <p>Lịch khám của bạn đã bị từ chối.</p>
        <p><b>Lý do:</b> {note or "Không có ghi chú"}</p>
        <p>Vui lòng đặt lịch khác.</p>
        """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html"
    )

    await fast_mail.send_message(message)
