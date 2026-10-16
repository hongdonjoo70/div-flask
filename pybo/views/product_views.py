import ast
from flask import render_template, Blueprint, request, g, jsonify
from pybo import db
from pybo.models import TourProduct, Review, ProductLike

bp = Blueprint('product', __name__, url_prefix='/product')

REGION_ALIAS = {
    'all': 'all',
    'sudo': 'sudo',
    'seoul': 'sudo',
    'gang': 'gang',
    'gangwon': 'gang',
    'chung': 'chung',
    'chungcheong': 'chung',
    'gyeong': 'gyeong',
    'geong': 'gyeong',
    'gyeongsang': 'gyeong',
    'jeon': 'jeon',
    'jeolla': 'jeon',
    'jeju': 'jeju'
}


def _parse_field_value(raw_val, expected_type, fallback):
    if isinstance(raw_val, expected_type):
        return raw_val
    if isinstance(raw_val, str) and raw_val.strip():
        try:
            parsed = ast.literal_eval(raw_val)
            if isinstance(parsed, expected_type):
                return parsed
        except Exception:
            pass
    return fallback


@bp.route('/main_product')
def main_product():
    kw = request.args.get('kw', default='', type=str).strip()
    raw_region = request.args.get('region', 'all').lower()
    selected_region = REGION_ALIAS.get(raw_region, 'all')

    query = TourProduct.query
    if kw:
        query = query.filter(TourProduct.name.ilike(f"%{kw}%"))

    products_data = query.all()

    return render_template(
        'product/main_product.html',
        products=products_data,
        selected_region=selected_region,
        kw=kw
    )


@bp.route('/sub_product/<int:product_id>')
def sub_product(product_id):
    selected_product = TourProduct.query.get_or_404(product_id)
    product_review = Review.query.filter_by(product_id=product_id).all()
    product_images = selected_product.get_image_list()
    product_itinerary = _parse_field_value(selected_product.itinerary_json, list, [])
    product_details = _parse_field_value(selected_product.detail_content, dict, {})
    is_liked = selected_product.is_liked_by(g.user) if g.user else False

    return render_template('product/sub_product.html',
                           product=selected_product,
                           reviews=product_review,
                           product_images=product_images,
                           product_itinerary=product_itinerary,
                           product_details=product_details,
                           is_liked=is_liked)


@bp.route('/sub_product/like', methods=['POST'])
def toggle_product_like():
    if not g.user:
        return jsonify({'error': 'unauthorized', 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json() or {}
    product_id = data.get('product_id')

    if not product_id:
        return jsonify({'error': 'bad_request'}), 400

    selected_product = TourProduct.query.get_or_404(product_id)
    existing_like = ProductLike.query.filter_by(user_id=g.user.id, product_id=product_id).first()

    if existing_like:
        selected_product.recommendation_count = max(0, (selected_product.recommendation_count or 0) - 1)
        db.session.delete(existing_like)
        status = "canceled"
    else:
        selected_product.recommendation_count = (selected_product.recommendation_count or 0) + 1
        db.session.add(ProductLike(user_id=g.user.id, product_id=product_id))
        status = "liked"

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'database_error', 'details': str(e)}), 500

    return jsonify({
        'success': True,
        'status': status,
        'recommendation_count': selected_product.recommendation_count
    }), 200



