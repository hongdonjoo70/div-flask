import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, g, flash
from pybo import db
from pybo.models import TourProduct, User, Order, OrderItem, Payment, Accommodation, OrderAccommodation
from pybo.forms import OrderReserveForm

bp = Blueprint('order', __name__, url_prefix='/order')


def check_is_member():
    """로그인 사용자 여부 판별 (g.user 및 Flask session 확인)"""
    if hasattr(g, 'user') and g.user:
        return True, g.user

    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return True, user

    return False, None


@bp.route("/reserve", methods=['GET'])
def reserve():
    """여행 상품 예약 및 여행객 정보 입력 화면"""
    product_id = request.args.get('product_id', type=int)
    headcount = request.args.get('headcount', 1, type=int)
    if headcount < 1:
        headcount = 1

    # 상품 정보 조회
    if not product_id:
        product = TourProduct.query.first()
        if not product:
            return "등록된 여행 상품이 없습니다.", 404
        product_id = product.id
    else:
        product = TourProduct.query.get_or_404(product_id)

    # 회원 / 비회원 여부 판별
    is_member, logged_user = check_is_member()

    # 가격 및 할인 계산
    unit_original_price = product.original_price
    unit_discount = product.get_discount_amount(is_member=is_member)
    unit_final_price = product.get_discounted_price(is_member=is_member)

    total_original = unit_original_price * headcount
    total_discount = unit_discount * headcount
    total_final = unit_final_price * headcount

    items_to_checkout = [{
        'product': product,
        'quantity': headcount,
        'original_price': unit_original_price,
        'final_price': unit_final_price,
        'subtotal_original': total_original,
        'subtotal_final': total_final
    }]

    today = datetime.now().date()
    min_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    max_date = (today + timedelta(days=14)).strftime('%Y-%m-%d')

    # 연관 숙박 (호텔/민박) 조회 (회원인 경우만 해당 권역 숙소 조회)
    accommodations = []
    hotels = []
    minbaks = []
    if is_member:
        accommodations = Accommodation.query.filter_by(region=product.region).order_by(Accommodation.category.desc(), Accommodation.price_per_night.asc()).all()
        hotels = [a for a in accommodations if a.category == '호텔']
        minbaks = [a for a in accommodations if a.category == '민박']

    form = OrderReserveForm(
        is_member=is_member,
        product_id=product.id,
        headcount=headcount,
        travel_date=min_date,
        guest_name=logged_user.name if (is_member and logged_user) else '',
        guest_phone=logged_user.phone if (is_member and logged_user) else '',
        guest_email=logged_user.email if (is_member and logged_user) else ''
    )

    return render_template(
        'order/reserve.html',
        form=form,
        product=product,
        items=items_to_checkout,
        headcount=headcount,
        min_date=min_date,
        max_date=max_date,
        is_member=is_member,
        logged_user=logged_user,
        unit_original_price=unit_original_price,
        unit_discount=unit_discount,
        unit_final_price=unit_final_price,
        total_original=total_original,
        total_discount=total_discount,
        total_final=total_final,
        direct_product_id=product.id,
        accommodations=accommodations,
        hotels=hotels,
        minbaks=minbaks
    )


@bp.route("/payment", methods=['POST'])
def payment():
    """예약 정보 및 여행객 목록 수신 후 결제 화면으로 이동"""
    is_member, logged_user = check_is_member()
    form = OrderReserveForm(is_member=is_member)

    # WTForms 기반 예약 폼 검증 (FlaskForm validate_on_submit)
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
        product_id = request.form.get('product_id', type=int) or 1
        headcount = request.form.get('headcount', 1, type=int) or 1
        return redirect(url_for('order.reserve', product_id=product_id, headcount=headcount))

    product = TourProduct.query.get_or_404(form.product_id.data)
    headcount = form.headcount.data or 1

    # 검증 완료된 약관 동의 값
    agree_special_val = bool(form.agree_special.data)
    agree_privacy_val = bool(form.agree_privacy.data)
    agree_sensitive_val = bool(form.agree_sensitive.data)
    agree_location_val = bool(form.agree_location.data)

    # 여행 날짜
    travel_date = (form.travel_date.data or '').strip()

    # 예약자 정보 수집
    if is_member and logged_user:
        reserver_name = logged_user.name
        reserver_phone = logged_user.phone
        reserver_email = logged_user.email
    else:
        reserver_name = (form.guest_name.data or '').strip() or '비회원 고객'
        reserver_phone = (form.guest_phone.data or '').strip()
        reserver_email = (form.guest_email.data or '').strip()

    # 여행객별 상세 정보 목록 수집 (이름, 성별, 전화번호)
    names = request.form.getlist('traveler_name[]')
    genders = request.form.getlist('traveler_gender[]')
    phones = request.form.getlist('traveler_phone[]')

    travelers = []
    for i in range(headcount):
        t_name = names[i].strip() if i < len(names) else ''
        t_gender = genders[i].strip() if i < len(genders) else '남'
        t_phone = phones[i].strip() if i < len(phones) else ''

        # 대표 여행자(1번) 정보가 비어있으면 예약자 정보로 대체
        if i == 0 and not t_name:
            t_name = reserver_name
        if i == 0 and not t_phone:
            t_phone = reserver_phone

        travelers.append({
            'index': i + 1,
            'name': t_name or f"여행객 {i + 1}",
            'gender': t_gender,
            'phone': t_phone or '-'
        })

    # 연관 숙박 상품 확인 (회원인 경우만 적용)
    accommodation_id = request.form.get('accommodation_id', type=int)
    selected_accommodation = None
    accommodation_price = 0
    if is_member and accommodation_id:
        selected_accommodation = Accommodation.query.get(accommodation_id)
        if selected_accommodation:
            accommodation_price = selected_accommodation.price_per_night

    # 결제 금액 계산
    unit_original_price = product.original_price
    unit_discount = product.get_discount_amount(is_member=is_member)
    unit_final_price = product.get_discounted_price(is_member=is_member)

    tour_original = unit_original_price * headcount
    tour_discount = unit_discount * headcount
    tour_final = unit_final_price * headcount

    total_original = tour_original + accommodation_price
    total_discount = tour_discount
    total_final = tour_final + accommodation_price

    return render_template(
        'order/payment.html',
        product=product,
        headcount=headcount,
        travel_date=travel_date,
        is_member=is_member,
        logged_user=logged_user,
        reserver_name=reserver_name,
        reserver_phone=reserver_phone,
        reserver_email=reserver_email,
        travelers=travelers,
        travelers_json=json.dumps(travelers, ensure_ascii=False),
        agree_special=agree_special_val,
        agree_privacy=agree_privacy_val,
        agree_sensitive=agree_sensitive_val,
        agree_location=agree_location_val,
        unit_original_price=unit_original_price,
        unit_discount=unit_discount,
        unit_final_price=unit_final_price,
        tour_original=tour_original,
        tour_discount=tour_discount,
        tour_final=tour_final,
        selected_accommodation=selected_accommodation,
        accommodation_price=accommodation_price,
        total_original=total_original,
        total_discount=total_discount,
        total_final=total_final
    )


@bp.route("/pay/complete", methods=['POST'])
def pay_complete():
    """결제 완료 처리 및 주문 저장"""
    product_id = request.form.get('product_id', type=int)
    headcount = request.form.get('headcount', 1, type=int)
    payment_method = request.form.get('payment_method', 'CARD')
    travel_date = request.form.get('travel_date', '').strip()

    product = TourProduct.query.get_or_404(product_id)
    is_member, logged_user = check_is_member()

    # 연관 숙박 상품 확인
    accommodation_id = request.form.get('accommodation_id', type=int)
    selected_accommodation = None
    accommodation_price = 0
    if is_member and accommodation_id:
        selected_accommodation = Accommodation.query.get(accommodation_id)
        if selected_accommodation:
            accommodation_price = selected_accommodation.price_per_night

    reserver_name = request.form.get('reserver_name', '')
    reserver_phone = request.form.get('reserver_phone', '')
    reserver_email = request.form.get('reserver_email', '')
    travelers_json = request.form.get('travelers_json', '[]')

    # 약관 동의 값 수신
    agree_special = request.form.get('agree_special') in ['1', 'on', 'true', 'True']
    agree_privacy = request.form.get('agree_privacy') in ['1', 'on', 'true', 'True']
    agree_sensitive = request.form.get('agree_sensitive') in ['1', 'on', 'true', 'True']
    agree_location = request.form.get('agree_location') in ['1', 'on', 'true', 'True']

    # PortOne 결제 응답 파라미터 수신
    portone_payment_id = request.form.get('portone_payment_id', '').strip()
    portone_tx_id = request.form.get('portone_tx_id', '').strip()
    paid_amount_str = request.form.get('paid_amount', '').strip()

    unit_final_price = product.get_discounted_price(is_member=is_member)
    unit_discount = product.get_discount_amount(is_member=is_member)
    tour_original = product.original_price * headcount
    tour_discount = unit_discount * headcount
    tour_final = unit_final_price * headcount

    total_original = tour_original + accommodation_price
    total_discount = tour_discount
    total_final = tour_final + accommodation_price

    # 실제 결제된 금액 (테스트 1,000원 결제 또는 정상 결제액)
    actual_paid = int(paid_amount_str) if (paid_amount_str and paid_amount_str.isdigit()) else total_final

    order_no = Order.generate_order_no()
    order = Order(
        order_no=order_no,
        user_id=logged_user.id if (is_member and logged_user) else None,
        guest_name=reserver_name if not is_member else None,
        guest_phone=reserver_phone if not is_member else None,
        guest_email=reserver_email if not is_member else None,
        original_amount=total_original,
        discount_amount=total_discount,
        status='COMPLETED',
        agree_special=agree_special,
        agree_privacy=agree_privacy,
        agree_sensitive=agree_sensitive,
        agree_location=agree_location,
        travel_date=travel_date
    )
    db.session.add(order)
    db.session.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=headcount,
        unit_price=unit_final_price,
        discount_applied=unit_discount
    )
    db.session.add(order_item)

    # 숙박 예약 레코드 저장
    if selected_accommodation:
        order_acc = OrderAccommodation(
            order_id=order.id,
            accommodation_id=selected_accommodation.id,
            nights=1,
            price_per_night=selected_accommodation.price_per_night,
            total_price=selected_accommodation.price_per_night,
            check_in_date=travel_date
        )
        db.session.add(order_acc)

    # PortOne 고유 payment_id / tx_id 우선 저장
    tx_id = portone_payment_id or portone_tx_id or f"TX-{order_no}"
    payment = Payment(
        order_id=order.id,
        payment_method=payment_method,
        paid_amount=actual_paid,
        transaction_id=tx_id,
        status='SUCCESS'
    )
    db.session.add(payment)
    db.session.commit()

    try:
        travelers = json.loads(travelers_json)
    except Exception:
        travelers = []

    return render_template(
        'order/complete.html',
        order=order,
        product=product,
        headcount=headcount,
        travel_date=travel_date,
        travelers=travelers,
        payment_method=payment_method,
        total_final=actual_paid,
        portone_payment_id=portone_payment_id or portone_tx_id,
        selected_accommodation=selected_accommodation
    )


@bp.route("/lookup", methods=['GET', 'POST'])
def lookup():
    """예약 확인 / 조회 화면
    - 로그인 시: 해당 회원의 예약 목록을 최신순(created_at desc)으로 표시, 항목 클릭 시 상세 표시
    - 비로그인 시: guest_name과 order_no를 입력받아 예약 검색, 로그인 상세와 동일한 정보 표시
    """
    is_member, logged_user = check_is_member()
    selected_order_no = request.args.get('order_no', '').strip()

    if is_member and logged_user:
        # 로그인 회원: 최신순 정렬하여 목록 조회
        orders = Order.query.filter_by(user_id=logged_user.id).order_by(Order.created_at.desc()).all()
        detail_order = None
        if selected_order_no:
            detail_order = Order.query.filter_by(order_no=selected_order_no, user_id=logged_user.id).first()

        return render_template(
            'order/lookup.html',
            is_member=True,
            logged_user=logged_user,
            orders=orders,
            detail_order=detail_order,
            selected_order_no=selected_order_no
        )
    else:
        # 비로그인(게스트): 폼 입력 기반 조회
        detail_order = None
        error_msg = None
        guest_name = ''
        order_no = ''

        if request.method == 'POST':
            guest_name = request.form.get('guest_name', '').strip()
            order_no = request.form.get('order_no', '').strip()

            if not guest_name or not order_no:
                error_msg = "예약자 성함과 주문번호를 모두 입력해주세요."
            else:
                target_order = Order.query.filter_by(order_no=order_no).first()
                if target_order:
                    # 비회원 주문자명 또는 회원 주문인 경우 회원명과 대조
                    match_name = (target_order.guest_name and target_order.guest_name.strip() == guest_name) or \
                                 (target_order.user and target_order.user.name.strip() == guest_name)
                    if match_name:
                        detail_order = target_order
                    else:
                        error_msg = "입력하신 예약자 성함이 일치하지 않습니다. 다시 확인해주세요."
                else:
                    error_msg = "입력하신 주문번호에 해당하는 예약 내역이 존재하지 않습니다."
        elif selected_order_no:
            # URL 파라미터로 직접 조회 요청 시
            target_order = Order.query.filter_by(order_no=selected_order_no).first()
            if target_order:
                detail_order = target_order

        return render_template(
            'order/lookup.html',
            is_member=False,
            logged_user=None,
            orders=[],
            detail_order=detail_order,
            guest_name=guest_name,
            order_no=order_no,
            error_msg=error_msg
        )


@bp.route("/detail/<order_no>", methods=['GET'])
def detail(order_no):
    """예약 상세 정보 페이지 (로그인/비로그인 공통 단독 화면)"""
    is_member, logged_user = check_is_member()
    order = Order.query.filter_by(order_no=order_no).first_or_404()

    # 회원인 경우 본인 주문인지 검증
    if is_member and logged_user and order.user_id and order.user_id != logged_user.id:
        flash('본인의 예약 내역만 열람하실 수 있습니다.', 'danger')
        return redirect(url_for('order.lookup'))

    return render_template(
        'order/detail.html',
        order=order,
        is_member=is_member,
        logged_user=logged_user
    )


@bp.route("/cancel/<order_no>", methods=['POST'])
def cancel(order_no):
    """예약 및 결제 취소 (주문 삭제)
    - 로그인 사용자: 본인의 주문인지 확인
    - 비로그인(게스트): guest_name 일치 여부 확인
    - 이용일(travel_date)이 지난 경우 취소 불가
    - 정상 검증 시 Order (및 cascade 연관 데이터) 삭제 처리
    """
    order = Order.query.filter_by(order_no=order_no).first()
    if not order:
        flash('존재하지 않는 주문 번호입니다.', 'danger')
        return redirect(url_for('order.lookup'))

    # 이용일 경과 여부 검증
    if order.is_past_travel_date:
        flash(f'여행 이용일({order.travel_date})이 지난 주문은 결제를 취소할 수 없습니다.', 'danger')
        return redirect(url_for('order.lookup'))

    is_member, logged_user = check_is_member()

    # 권한 검증
    if order.user_id:
        # 회원 주문인 경우 로그인 본인 확인
        if not (is_member and logged_user and order.user_id == logged_user.id):
            flash('해당 주문을 취소할 권한이 없습니다.', 'danger')
            return redirect(url_for('order.lookup'))
    else:
        # 비회원 주문인 경우 게스트 성명 검증
        guest_name = request.form.get('guest_name', '').strip()
        if not guest_name or (order.guest_name and order.guest_name.strip() != guest_name):
            flash('예약자 성함이 일치하지 않아 취소할 수 없습니다.', 'danger')
            return redirect(url_for('order.lookup'))

    cancelled_order_no = order.order_no
    db.session.delete(order)
    db.session.commit()

    flash(f'주문번호 {cancelled_order_no}의 예약 및 결제가 성공적으로 취소(삭제)되었습니다.', 'success')
    return redirect(url_for('order.lookup'))


