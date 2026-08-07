<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { config, functions, models, settings } from '$shared/stores';
	import { updateFunctionById, getFunctions, getFunctionById } from '$api/functions';

	import FunctionEditor from '$features/admin/Functions/FunctionEditor.svelte';
	import Spinner from '$shared/components/Spinner.svelte';
	import { getModels } from '$api';
	import { compareVersion, extractFrontmatter } from '$shared/utils';
	import { JYOTIGPT_VERSION } from '$shared/constants';

	const i18n = getContext('i18n');

	let func = null;

	const saveHandler = async (data) => {
		console.log(data);

		const manifest = extractFrontmatter(data.content);
		if (compareVersion(manifest?.required_JYOTIGPT_version ?? '0.0.0', JYOTIGPT_VERSION)) {
			console.log('Version is lower than required');
			toast.error(
				$i18n.t(
					'JyotiGPT version (v{{JYOTIGPT_VERSION}}) is lower than required version (v{{REQUIRED_VERSION}})',
					{
						JYOTIGPT_VERSION: JYOTIGPT_VERSION,
						REQUIRED_VERSION: manifest?.required_JYOTIGPT_version ?? '0.0.0'
					}
				)
			);
			return;
		}

		const res = await updateFunctionById(localStorage.token, func.id, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Function updated successfully'));
			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	onMount(async () => {
		console.log('mounted');
		const id = $page.url.searchParams.get('id');

		if (id) {
			func = await getFunctionById(localStorage.token, id).catch((error) => {
				toast.error(`${error}`);
				goto('/admin/functions');
				return null;
			});

			console.log(func);
		}
	});
</script>

{#if func}
	<FunctionEditor
		edit={true}
		id={func.id}
		name={func.name}
		meta={func.meta}
		content={func.content}
		onSave={(value) => {
			saveHandler(value);
		}}
	/>
{:else}
	<div class="flex items-center justify-center h-full">
		<div class=" pb-16">
			<Spinner />
		</div>
	</div>
{/if}
